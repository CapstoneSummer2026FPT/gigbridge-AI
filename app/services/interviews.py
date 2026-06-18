"""Interview service — handles stateful, voice-enabled AI candidate screening.

Key changes from the in-memory version:
  - Conversation history is stored in Redis (not MemoryManager)
  - Voice operations delegate to VoiceService facade (gateway + session)
  - Atomic confirm flow: GETDEL draft → verify → generate next → TTS → advance pointer
  - Pointer advances ONLY after TTS is confirmed (atomic guarantee)
"""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.api.schemas.interviews import (
    StartInterviewRequest,
    InterviewQuestionResponse,
    InterviewFeedback,
    DraftDataResponse,
)
from app.core.config import settings
from app.core.exceptions import (
    VoiceProviderException,
    SessionExpiredError,
    DraftExpiredError,
    ConfirmConflictError,
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.voice import VoiceService, get_voice_service
from app.clients.voice.models import DraftData

logger = logging.getLogger("ai_server.interviews_service")


class InterviewService:
    """Stateful interview service with voice support and atomic confirm flow.

    The interview lifecycle:
      initialize() → [transcribe_audio() → confirm_answer()]* → complete
    """

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        voice_service: Optional[VoiceService] = None,
    ):
        self.llm = llm_gateway
        self.voice = voice_service
        self.max_questions = settings.MAX_INTERVIEW_QUESTIONS

    # ── Interview Lifecycle ────────────────────────────────────

    async def initialize_interview(
        self, request: StartInterviewRequest
    ) -> InterviewQuestionResponse:
        """Initialize a new interview session.

        Creates a Redis-backed session, generates the first question
        via LLM, synthesizes TTS if voice mode, and returns everything.
        """
        session_data = {
            "job_id": request.job_id,
            "freelancer_id": request.freelancer_id,
            "mode": request.mode or "text",
            "language": request.language or "vi",
            "question_index": 1,
        }

        session = await self.voice.create_session(session_data)
        logger.info(
            "Interview initialized: %s (lang=%s, mode=%s)",
            session.session_id, session.language, session.mode,
        )

        # Retrieve job details (from LLM or defaults)
        job_title = "Software Developer"
        job_skills = ["Software Engineering"]

        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Keep questions concise, professional, and targeted at assessing specific technical skills.\n"
            "Ask only one question at a time. Introduce yourself and ask the first question."
        )
        user_prompt = (
            f"Start the interview for a {job_title} position.\n"
            f"Key Skills to evaluate: {', '.join(job_skills)}.\n"
            "Generate the first ice-breaker technical question."
        )

        first_question = await self.llm.generate(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

        # Save assistant message to history
        await self.voice.add_history(
            session.session_id, "assistant", first_question, session.language
        )

        # TTS synthesis for voice mode
        audio_base64 = None
        audio_mime_type = None
        tts_provider = None
        fallback_used = False

        if session.mode == "voice":
            try:
                tts_result = await self.voice.text_to_speech(
                    first_question, session.language
                )
                audio_base64 = base64.b64encode(tts_result.audio_bytes).decode("utf-8")
                audio_mime_type = tts_result.mime_type
                tts_provider = tts_result.tts_provider
                fallback_used = tts_result.fallback_used
            except VoiceProviderException as exc:
                logger.warning("TTS failed for first question: %s", exc)
                # Continue without audio — frontend shows text only

        return InterviewQuestionResponse(
            session_id=session.session_id,
            question_index=1,
            question_text=first_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
            is_completed=False,
        )

    # ── Text Answer (backward compat) ─────────────────────────

    async def process_answer(
        self, session_id: str, answer_text: str
    ) -> InterviewQuestionResponse:
        """Process a text-mode answer (no audio).

        This is the text equivalent of transcribe_audio + confirm_answer
        combined into one step. For voice interviews, use the two-step flow.

        Args:
            session_id: Active interview session.
            answer_text: The candidate's text answer.

        Returns:
            Next question or final evaluation.
        """
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        # Save answer to history
        await self.voice.add_history(
            session_id, "user", answer_text, session.language
        )

        # Check if interview is complete
        if session.question_index >= self.max_questions:
            feedback = await self._generate_feedback(session_id)
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                is_completed=True,
                feedback=feedback,
            )

        # Generate next question
        next_index = session.question_index + 1
        history = await self.voice.get_history(session_id)
        next_question = await self._generate_next_question(history, session.language)

        # Synthesize TTS if voice mode
        audio_base64 = None
        audio_mime_type = None
        if session.mode == "voice":
            tts_result = await self._synthesize_question(
                session_id, next_index, next_question, session.language
            )
            if tts_result:
                audio_base64 = base64.b64encode(tts_result.audio_bytes).decode("utf-8")
                audio_mime_type = tts_result.mime_type

        # Advance pointer
        await self.voice.advance_pointer(session_id)

        # Save assistant question to history
        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )

        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_text=next_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            is_completed=False,
        )

    # ── Transcribe (Step 1 of Atomic Confirm) ──────────────────

    async def transcribe_audio(
        self, session_id: str, pcm_wav_bytes: bytes, language: Optional[str] = None
    ) -> DraftDataResponse:
        """Transcribe audio and save a draft (does NOT advance the session).

        This is step 1 of the atomic confirm flow:
          1. Load session (fail fast if expired)
          2. STT transcribe (with provider fallback)
          3. Save draft as JSON (10-minute TTL)

        Args:
            session_id: Active interview session.
            pcm_wav_bytes: Decoded WAV 16-bit 16kHz mono PCM bytes.
            language: Optional override; defaults to session language.

        Returns:
            DraftDataResponse with transcript and metadata.

        Raises:
            SessionExpiredError: If session not found or expired.
            VoiceProviderException: If all STT providers fail.
        """
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        lang = language or session.language
        result = await self.voice.speech_to_text(pcm_wav_bytes, lang)

        draft = DraftData(
            draft_id=f"draft_{uuid.uuid4().hex[:8]}",
            question_index=session.question_index,
            transcript=result.text,
            language=lang,
            stt_provider=result.stt_provider,
            confidence=result.confidence,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await self.voice.save_draft(session_id, draft)

        expires_at = (
            datetime.now(timezone.utc).isoformat()
        )  # actual TTL tracked by Redis

        logger.info(
            "Transcribed: session=%s q=%d stt=%s conf=%.2f",
            session_id, session.question_index, result.stt_provider, result.confidence,
        )

        return DraftDataResponse(
            session_id=session_id,
            draft_id=draft.draft_id,
            question_index=draft.question_index,
            transcript=draft.transcript,
            language=draft.language,
            stt_provider=draft.stt_provider,
            confidence=draft.confidence,
            fallback_used=result.fallback_used,
            expires_at=expires_at,
        )

    # ── Confirm Answer (Step 2 of Atomic Confirm) ──────────────

    async def confirm_answer(
        self, session_id: str, corrected_text: Optional[str] = None
    ) -> InterviewQuestionResponse:
        """Atomically confirm an answer and advance the interview.

        Canonical order (critical — must be followed exactly):
          1. Load session — fail fast if expired
          2. GETDEL draft — atomic consume (prevents double-confirm)
          3. Distinguish draft_expired vs confirm_conflict
          4. Determine final answer (corrected_text or draft.transcript)
          5. Save answer to Redis history
          6. If interview complete → generate feedback, return
          7. Generate NEXT question text via LLM
          8. Synthesize TTS (check cache first)
          9. Cache TTS for next time
          10. Advance pointer (ONLY after TTS is confirmed)
          11. Save assistant question to history
          12. Return next question

        IMPORTANT: Step 7-10 run BEFORE pointer advance (step 11).
        If TTS fails, pointer stays and confirm can be retried.
        """
        # 1. Load session
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        # 2. Atomic draft consume via GETDEL
        draft = await self.voice.consume_draft(session_id)
        if not draft:
            # 3. Distinguish: was it expired or already confirmed?
            if await self.voice.is_confirmed(session_id):
                raise ConfirmConflictError()
            raise DraftExpiredError()

        # 4. Determine final answer
        final_answer = (corrected_text or draft.transcript).strip()
        if not final_answer:
            raise DraftExpiredError("draft_expired")

        # 5. Save answer to history
        await self.voice.add_history(
            session_id, "user", final_answer, draft.language
        )
        # Mark as confirmed (for conflict detection on double-confirm)
        await self.voice.mark_confirmed(session_id)

        # 6. Check if interview is complete
        if session.question_index >= self.max_questions:
            feedback = await self._generate_feedback(session_id)
            logger.info("Interview complete: %s", session_id)
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                is_completed=True,
                feedback=feedback,
            )

        # 7. Generate next question (BEFORE advancing pointer)
        next_index = session.question_index + 1
        history = await self.voice.get_history(session_id)
        next_question = await self._generate_next_question(history, session.language)

        # 8. Synthesize TTS (check cache first)
        audio_base64 = None
        audio_mime_type = None
        tts_provider = None
        fallback_used = False

        if session.mode == "voice":
            tts_result = await self._synthesize_question(
                session_id, next_index, next_question, session.language
            )
            if tts_result:
                audio_base64 = base64.b64encode(tts_result.audio_bytes).decode("utf-8")
                audio_mime_type = tts_result.mime_type
                tts_provider = tts_result.tts_provider
                fallback_used = tts_result.fallback_used

        # 10. Advance pointer (atomic — ONLY after TTS/LLM confirmed)
        await self.voice.advance_pointer(session_id)

        # 11. Save assistant question to history
        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )

        logger.info(
            "Confirm → advance: session=%s q=%d→%d tts=%s",
            session_id, session.question_index, next_index, tts_provider or "none",
        )

        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_text=next_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
            is_completed=False,
        )

    # ── Private helpers ────────────────────────────────────────

    async def _generate_next_question(self, history: list[dict], language: str) -> str:
        """Generate the next interview question based on conversation history."""
        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Analyze the transcript and user's answers. Ask the next follow-up question "
            "to probe deeper into their technical experience.\n"
            "Keep questions concise, professional, and ask only one question at a time.\n"
            f"Respond in the interview's language ({language})."
        )
        user_prompt = "Generate the next question based on the candidate's last response."

        return await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
        )

    async def _synthesize_question(
        self, session_id: str, question_index: int, text: str, language: str
    ):
        """Synthesize TTS for a question, checking cache first."""
        # Check cache
        cached = await self.voice.get_cached_tts(session_id, question_index)
        if cached is not None:
            from app.clients.voice.models import SynthesisResult
            return SynthesisResult(
                audio_bytes=cached,
                mime_type="audio/mpeg",
                tts_provider="cache",
            )

        # Synthesize and cache
        try:
            tts_result = await self.voice.text_to_speech(text, language)
            await self.voice.cache_tts(session_id, question_index, tts_result.audio_bytes)
            return tts_result
        except VoiceProviderException as exc:
            logger.warning("TTS synthesis failed for q=%d: %s", question_index, exc)
            return None

    async def _generate_feedback(self, session_id: str) -> InterviewFeedback:
        """Generate evaluation feedback from the full conversation history."""
        history = await self.voice.get_history(session_id)

        system_prompt = (
            "You are an expert technical interviewer evaluating a candidate's transcript.\n"
            "Evaluate the candidate transcript and return a final hiring decision.\n"
            "Output ONLY a JSON object matching this schema:\n"
            "{\n"
            '  "score": 85,\n'
            '  "summary": "Detailed summary...",\n'
            '  "technical_skills": ["React", "API Integration"],\n'
            '  "soft_skills": ["Communication"],\n'
            '  "recommended_hire": true\n'
            "}"
        )
        user_prompt = "Perform the evaluation on the conversation history provided."

        evaluation_json = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
            response_format=InterviewFeedback,
        )

        return InterviewFeedback.model_validate_json(evaluation_json)


# ── Dependency injection ────────────────────────────────────────

async def get_interview_service() -> InterviewService:
    """Return an InterviewService with all dependencies wired.

    This replaces the old synchronous singleton with an async factory
    that awaits the VoiceService singleton initialization.
    """
    llm = get_llm_gateway()
    voice = await get_voice_service()
    return InterviewService(llm_gateway=llm, voice_service=voice)
