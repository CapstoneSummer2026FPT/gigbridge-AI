"""Interview service — handles stateful, voice-enabled AI candidate screening.

Key changes from the in-memory version:
  - Conversation history is stored in Redis (not MemoryManager)
  - Voice operations delegate to VoiceService facade (gateway + session)
  - Atomic confirm flow: GETDEL draft → verify → generate next → advance pointer
  - Question text advances first; voice audio is generated lazily in the background
"""

import asyncio
import base64
import hashlib
import json
import logging
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from app.api.schemas.interviews import (
    StartInterviewRequest,
    InterviewQuestionResponse,
    InterviewFeedback,
    DraftDataResponse,
    AnalyzeVettingRequest,
)
from app.core.config import settings
from app.core.exceptions import (
    VoiceProviderException,
    SessionExpiredError,
    DraftExpiredError,
    ConfirmConflictError,
    InvalidAnswerError,
    SessionAccessDeniedError,
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.voice import VoiceService, get_voice_service
from app.services.transcript_corrector import TranscriptCorrector
from app.clients.voice.models import DraftData, SynthesisResult
from app.services.tts_audio_stitcher import TTSAudioStitcher
from app.services.hotword_resolver import HotwordResolver

logger = logging.getLogger("ai_server.interviews_service")


class InterviewService:
    """Stateful interview service with voice support and atomic confirm flow.

    The interview lifecycle:
      initialize() → [transcribe_audio() → confirm_answer()]* → complete
    """

    def __init__(
        self,
        llm_gateway: LLMGateway | None = None,
        voice_service: VoiceService | None = None,
        hotword_resolver: HotwordResolver | None = None,
    ):
        self.llm = llm_gateway
        self.voice = voice_service
        self.max_questions = settings.MAX_INTERVIEW_QUESTIONS
        self.transcript_corrector = TranscriptCorrector()
        self.hotword_resolver = hotword_resolver or HotwordResolver()
        self._pending_tts_tasks: set[asyncio.Task] = set()

    # ── Interview Lifecycle ────────────────────────────────────

    async def initialize_interview(
        self, request: StartInterviewRequest
    ) -> InterviewQuestionResponse:
        """Initialize a new interview session.

        Creates a Redis-backed session, generates the first question
        via LLM, synthesizes TTS if voice mode, and returns everything.
        """
        started_at = time.perf_counter()
        job_title = request.job_title.strip()
        job_description = (request.job_description or "").strip()
        job_skills = self._clean_terms(request.job_skills)
        job_phonetic_aliases = self._clean_aliases(request.job_phonetic_aliases)
        hotwords = self.hotword_resolver.resolve(
            job_title,
            job_skills,
            job_major=request.job_major,
            job_category=request.job_category,
            job_questions=request.job_questions,
            phonetic_aliases=job_phonetic_aliases,
        )
        interview_language = self._resolve_interview_language(
            request.language,
            job_title,
            job_description,
        )
        audio_access_token = secrets.token_urlsafe(32)

        session_data = {
            "job_id": request.job_id,
            "freelancer_id": request.freelancer_id,
            "mode": request.mode or "text",
            "language": interview_language,
            "stt_language": (request.language or "auto").strip().lower(),
            "audio_access_token_hash": hashlib.sha256(
                audio_access_token.encode("utf-8")
            ).hexdigest(),
            "question_index": 1,
            "question_count": (
                len(request.job_questions)
                if request.job_questions
                else request.question_count or self.max_questions
            ),
            "job_title": job_title,
            "job_description": job_description,
            "job_skills": job_skills,
            "hotwords": hotwords,
            "job_phonetic_aliases": job_phonetic_aliases,
            "job_questions": request.job_questions or [],
        }

        session_create_started = time.perf_counter()
        session = await self.voice.create_session(session_data)
        session_create_ms = (time.perf_counter() - session_create_started) * 1000
        logger.info(
            "Interview initialized: %s (lang=%s, mode=%s)",
            session.session_id, session.language, session.mode,
        )

        job_title = session.job_title
        job_description = session.job_description
        job_skills = session.job_skills or []
        skill_line = ", ".join(job_skills) if job_skills else "No structured skills were supplied; infer from the job description."
        language_name = self._language_name(session.language)

        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Keep questions concise, professional, and targeted at assessing specific technical skills.\n"
            "Ask only one question at a time. Keep the response natural for a spoken interview.\n"
            f"Respond only in {language_name}. Keep programming languages, frameworks, tools, and product names unchanged."
        )
        user_prompt = (
            f"Start the interview for a {job_title} position.\n"
            f"Job requirements: {job_description or 'No job description was supplied.'}\n"
            f"Key skills to evaluate: {skill_line}.\n"
            "Generate the first ice-breaker technical question."
        )

        llm_started = time.perf_counter()
        if session.job_questions:
            first_question = session.job_questions[0]
            llm_ms = 0.0
        else:
            first_question = await self.llm.generate(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            llm_ms = (time.perf_counter() - llm_started) * 1000

        # Save assistant message to history
        history_started = time.perf_counter()
        await self.voice.add_history(
            session.session_id, "assistant", first_question, session.language
        )
        history_ms = (time.perf_counter() - history_started) * 1000

        # Voice audio is generated only when the browser opens the streaming
        # endpoint. This avoids duplicate eager synthesis and lets playback
        # begin with the provider's first audio frame.
        audio_base64 = None
        audio_mime_type = None
        tts_provider = None
        fallback_used = False
        tts_ms = 0.0

        if session.mode == "voice":
            tts_started = time.perf_counter()
            tts_ms = (time.perf_counter() - tts_started) * 1000
            tts_provider = "streaming"

        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Interview initialize timing: session=%s total=%.0fms redis_create=%.0fms llm=%.0fms history=%.0fms tts=%.0fms mode=%s llm_provider=%s tts_provider=%s",
            session.session_id,
            total_ms,
            session_create_ms,
            llm_ms,
            history_ms,
            tts_ms,
            session.mode,
            getattr(self.llm, "default_provider", "unknown"),
            tts_provider or "none",
        )

        return InterviewQuestionResponse(
            session_id=session.session_id,
            audio_access_token=audio_access_token,
            question_index=1,
            question_count=len(session.job_questions) or session.question_count,
            question_text=first_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
            is_completed=False,
            job_id=session.job_id,
            freelancer_id=session.freelancer_id,
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
        if session.question_index >= (len(session.job_questions) or session.question_count):
            feedback = await self._generate_feedback(session_id)
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                question_count=len(session.job_questions) or session.question_count,
                is_completed=True,
                feedback=feedback,
            )

        # Generate next question
        next_index = session.question_index + 1
        history = await self.voice.get_history(session_id)
        next_question = await self._generate_next_question(history, session.language)

        # Voice audio is streamed lazily when requested by the frontend.
        audio_base64 = None
        audio_mime_type = None
        tts_provider = None
        fallback_used = False
        if session.mode == "voice":
            tts_provider = "streaming"

        # Advance pointer
        await self.voice.advance_pointer(session_id)

        # Save assistant question to history
        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )
        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_count=len(session.job_questions) or session.question_count,
            question_text=next_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
            is_completed=False,
        )

    # ── Transcribe (Step 1 of Atomic Confirm) ──────────────────

    async def transcribe_audio(
        self, session_id: str, pcm_wav_bytes: bytes, language: str | None = None
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
        started_at = time.perf_counter()
        load_started = time.perf_counter()
        session = await self.voice.load_session(session_id)
        load_ms = (time.perf_counter() - load_started) * 1000
        if not session:
            raise SessionExpiredError()

        requested_language = (
            language
            if language is not None
            else session.stt_language or session.language or "auto"
        ).strip().lower()
        stt_started = time.perf_counter()
        result = await self.voice.speech_to_text(
            pcm_wav_bytes,
            requested_language,
            hotwords=session.hotwords or [],
            primary_language=session.language,
        )
        stt_ms = (time.perf_counter() - stt_started) * 1000
        draft_language = result.language or requested_language
        correction_started = time.perf_counter()
        correction = self.transcript_corrector.correct(
            result.text,
            hotwords=session.hotwords or [],
            phonetic_aliases=session.job_phonetic_aliases or {},
            language=draft_language,
        )
        correction_ms = (time.perf_counter() - correction_started) * 1000
        transcript = correction.corrected_text or result.text

        draft = DraftData(
            draft_id=f"draft_{uuid.uuid4().hex}",
            question_index=session.question_index,
            transcript=transcript,
            language=draft_language,
            stt_provider=result.stt_provider,
            confidence=result.confidence,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        save_started = time.perf_counter()
        await self.voice.save_draft(session_id, draft)
        save_ms = (time.perf_counter() - save_started) * 1000

        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=settings.REDIS_DRAFT_TTL)
        ).isoformat()

        logger.info(
            "Transcribed: session=%s q=%d stt=%s conf=%.2f corrected=%s",
            session_id,
            session.question_index,
            result.stt_provider,
            result.confidence,
            correction.changed,
        )
        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Interview transcribe timing: session=%s total=%.0fms load_session=%.0fms stt=%.0fms correction=%.0fms save_draft=%.0fms stt_provider=%s audio_bytes=%d reason=\"stt includes provider model/API time; first faster_whisper call may include model lazy-load\"",
            session_id,
            total_ms,
            load_ms,
            stt_ms,
            correction_ms,
            save_ms,
            result.stt_provider,
            len(pcm_wav_bytes),
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
        self, session_id: str, corrected_text: str | None = None
    ) -> InterviewQuestionResponse:
        """Atomically confirm an answer and advance the interview.

        Canonical order (critical — must be followed exactly):
          1. Load session — fail fast if expired
          2. GETDEL draft — atomic consume (prevents double-confirm)
          3. Distinguish draft_expired vs confirm_conflict
          4. Determine final answer (corrected_text or draft.transcript)
          5. Save answer to Redis history
          6. If interview complete → generate feedback, return
          7. Generate the next question text via LLM
          8. Advance the question pointer
          9. Save the assistant question to history
          10. Schedule lazy background TTS for voice mode
          11. Return immediately with tts_provider="pending"

        """
        if corrected_text is not None and not corrected_text.strip():
            raise InvalidAnswerError()
        # 1. Load session
        started_at = time.perf_counter()
        load_started = time.perf_counter()
        session = await self.voice.load_session(session_id)
        load_ms = (time.perf_counter() - load_started) * 1000
        if not session:
            raise SessionExpiredError()

        # 2. Atomic draft consume via GETDEL
        consume_started = time.perf_counter()
        draft = await self.voice.consume_draft(session_id)
        consume_ms = (time.perf_counter() - consume_started) * 1000
        if not draft:
            # 3. Distinguish: was it expired or already confirmed?
            if await self.voice.is_confirmed(session_id):
                raise ConfirmConflictError()
            raise DraftExpiredError()

        # 4. Determine final answer
        final_answer = (corrected_text or draft.transcript).strip()
        if not final_answer:
            raise InvalidAnswerError()

        # 5. Save answer to history
        answer_history_started = time.perf_counter()
        await self.voice.add_history(
            session_id, "user", final_answer, draft.language
        )
        # Mark as confirmed (for conflict detection on double-confirm)
        await self.voice.mark_confirmed(session_id)
        answer_history_ms = (time.perf_counter() - answer_history_started) * 1000

        # 6. Check if interview is complete
        question_count = len(session.job_questions) or session.question_count
        is_complete = session.question_index >= question_count

        if is_complete:
            feedback_started = time.perf_counter()
            feedback = await self._generate_feedback(session_id)
            feedback_ms = (time.perf_counter() - feedback_started) * 1000
            total_ms = (time.perf_counter() - started_at) * 1000
            logger.info("Interview complete: %s", session_id)
            logger.info(
                "Interview confirm timing: session=%s total=%.0fms load_session=%.0fms consume_draft=%.0fms answer_history=%.0fms feedback=%.0fms completed=true reason=\"feedback includes LLM evaluation over Redis conversation history\"",
                session_id,
                total_ms,
                load_ms,
                consume_ms,
                answer_history_ms,
                feedback_ms,
            )
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                question_count=question_count,
                is_completed=True,
                feedback=feedback,
                job_id=session.job_id,
                freelancer_id=session.freelancer_id,
            )

        # 7. Generate next question (BEFORE advancing pointer)
        next_index = session.question_index + 1
        get_history_started = time.perf_counter()
        history = await self.voice.get_history(session_id)
        get_history_ms = (time.perf_counter() - get_history_started) * 1000
        llm_started = time.perf_counter()
        if session.job_questions:
            next_question = session.job_questions[session.question_index]
            llm_ms = 0.0
        else:
            next_question = await self._generate_next_question(history, session.language)
            llm_ms = (time.perf_counter() - llm_started) * 1000

        # 8. Prepare lazy streaming TTS. The full question text returns
        # immediately; synthesis starts when the browser requests playback.
        audio_base64 = None
        audio_mime_type = None
        tts_provider = None
        fallback_used = False
        tts_ms = 0.0

        if session.mode == "voice":
            tts_started = time.perf_counter()
            tts_ms = (time.perf_counter() - tts_started) * 1000
            tts_provider = "streaming"

        # 8. Advance the pointer after the LLM question is ready.
        advance_started = time.perf_counter()
        await self.voice.advance_pointer(session_id)
        advance_ms = (time.perf_counter() - advance_started) * 1000

        # 9. Save the assistant question to history. TTS opens on demand.
        assistant_history_started = time.perf_counter()
        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )
        assistant_history_ms = (time.perf_counter() - assistant_history_started) * 1000
        logger.info(
            "Confirm → advance: session=%s q=%d→%d tts=%s",
            session_id, session.question_index, next_index, tts_provider or "none",
        )

        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Interview confirm timing: session=%s total=%.0fms load_session=%.0fms consume_draft=%.0fms answer_history=%.0fms get_history=%.0fms llm=%.0fms tts=%.0fms advance_pointer=%.0fms assistant_history=%.0fms completed=false llm_provider=%s tts_provider=%s reason=\"llm generates next question; tts includes cache lookup plus provider synthesis when voice mode is used\"",
            session_id,
            total_ms,
            load_ms,
            consume_ms,
            answer_history_ms,
            get_history_ms,
            llm_ms,
            tts_ms,
            advance_ms,
            assistant_history_ms,
            getattr(self.llm, "default_provider", "unknown"),
            tts_provider or "none",
        )

        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_count=question_count,
            question_text=next_question,
            language=session.language,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
            is_completed=False,
            job_id=session.job_id,
            freelancer_id=session.freelancer_id,
        )

    # ── Private helpers ────────────────────────────────────────

    async def _generate_next_question(self, history: list[dict], language: str) -> str:
        """Generate the next interview question based on conversation history."""
        language_name = self._language_name(language)
        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Analyze the transcript and user's answers. Ask the next follow-up question "
            "to probe deeper into their technical experience.\n"
            "Keep questions concise, professional, and ask only one question at a time.\n"
            f"Respond only in {language_name}. Keep programming languages, frameworks, tools, and product names unchanged."
        )
        user_prompt = "Generate the next question based on the candidate's last response."

        return await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
        )

    @classmethod
    def _resolve_interview_language(
        cls,
        requested_language: str | None,
        job_title: str,
        job_description: str,
    ) -> str:
        requested = (requested_language or "auto").strip().lower().replace("_", "-")
        if requested in {"vi", "vi-vn", "vietnamese"}:
            return "vi"
        if requested in {"en", "en-us", "en-gb", "english"}:
            return "en"
        return cls._infer_job_language(job_title, job_description)

    @staticmethod
    def _infer_job_language(job_title: str, job_description: str) -> str:
        text = f"{job_title} {job_description}".lower()
        if not text.strip():
            return "vi"

        vietnamese_diacritics = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
        if any(char in text for char in vietnamese_diacritics):
            return "vi"

        vietnamese_words = {
            "va", "hoac", "cho", "voi", "cac", "nhung", "ung", "vien",
            "cong", "viec", "du", "an", "kinh", "nghiem", "ky", "nang",
            "lap", "trinh", "thiet", "ke", "phat", "trien", "yeu", "cau",
        }
        tokens = set(re.findall(r"[a-zA-Z]+", text))
        vietnamese_hits = len(tokens & vietnamese_words)
        return "vi" if vietnamese_hits >= 3 else "en"

    @staticmethod
    def _language_name(language: str) -> str:
        return "Vietnamese" if (language or "").lower().startswith("vi") else "English"

    @staticmethod
    def _clean_terms(terms: list[str]) -> list[str]:
        seen = set()
        cleaned = []
        for term in terms or []:
            value = str(term).strip()
            key = value.casefold()
            if value and key not in seen:
                cleaned.append(value)
                seen.add(key)
        return cleaned

    @classmethod
    def _build_hotwords(
        cls,
        job_title: str,
        job_skills: list[str],
        job_description: str | None = None,
        job_major: str | None = None,
        job_category: str | None = None,
        job_questions: list[str] | None = None,
        phonetic_aliases: dict[str, list[str]] | None = None,
    ) -> list[str]:
        """Compatibility wrapper for deterministic hotword construction."""
        return HotwordResolver.build_reliable_terms(
            job_title,
            job_skills,
            job_major=job_major,
            job_category=job_category,
            job_questions=job_questions,
            phonetic_aliases=phonetic_aliases,
            max_terms=settings.HOTWORD_MAX_TERMS,
        )

    @staticmethod
    def _clean_aliases(aliases: dict[str, list[str]]) -> dict[str, list[str]]:
        cleaned: dict[str, list[str]] = {}
        for canonical, values in (aliases or {}).items():
            canonical_text = str(canonical).strip()
            if not canonical_text:
                continue
            alias_values = []
            seen = set()
            for value in values or []:
                alias = str(value).strip()
                key = alias.casefold()
                if alias and key not in seen:
                    alias_values.append(alias)
                    seen.add(key)
            if alias_values:
                cleaned[canonical_text] = alias_values
        return cleaned

    async def schedule_question_tts(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: list[str] | None = None,
    ) -> None:
        """Schedule background TTS generation for a question."""
        cached = await self.voice.get_cached_tts(session_id, question_index)
        if cached is not None:
            return

        status = await self.voice.get_tts_status(session_id, question_index)
        if status.get("status") in {"pending", "ready"}:
            return

        await self.voice.set_tts_status(session_id, question_index, "pending")
        task = asyncio.create_task(
            self._generate_question_tts_background(
                session_id,
                question_index,
                text,
                language,
                hotwords=hotwords or [],
            )
        )
        self._pending_tts_tasks.add(task)
        task.add_done_callback(self._finish_background_tts_task)

    async def get_question_audio(
        self, session_id: str, question_index: int, audio_access_token: str
    ) -> dict:
        """Return cached question audio or current background generation status."""
        if not await self.voice.verify_audio_access_token(
            session_id, audio_access_token
        ):
            raise SessionAccessDeniedError()
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        cached = await self.voice.get_cached_tts(session_id, question_index)
        if cached is not None:
            meta = await self.voice.get_cached_tts_meta(session_id, question_index)
            return {
                "session_id": session_id,
                "question_index": question_index,
                "status": "ready",
                "audio_base64": base64.b64encode(cached).decode("utf-8"),
                "audio_mime_type": meta["mime_type"],
                "tts_provider": meta["tts_provider"],
                "fallback_used": meta["fallback_used"],
                "error": None,
            }

        status = await self.voice.get_tts_status(session_id, question_index)
        if status.get("status") == "missing":
            text = await self._find_question_text(session_id, question_index)
            if text:
                await self.schedule_question_tts(
                    session_id,
                    question_index,
                    text,
                    session.language,
                    hotwords=session.hotwords or [],
                )
                status = {"status": "pending", "error": None}

        return {
            "session_id": session_id,
            "question_index": question_index,
            "status": status.get("status", "pending"),
            "audio_base64": None,
            "audio_mime_type": None,
            "tts_provider": None,
            "fallback_used": False,
            "error": (
                "tts_generation_failed"
                if status.get("status") == "failed"
                else None
            ),
        }

    async def stream_question_audio(
        self,
        session_id: str,
        question_index: int,
        audio_access_token: str,
    ):
        """Open immediate single-voice audio for one interview question."""
        if not await self.voice.verify_audio_access_token(
            session_id, audio_access_token
        ):
            raise SessionAccessDeniedError()
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        cached = await self.voice.get_cached_tts(session_id, question_index)
        if cached is not None:
            meta = await self.voice.get_cached_tts_meta(session_id, question_index)

            async def cached_stream():
                for offset in range(0, len(cached), 64 * 1024):
                    yield cached[offset : offset + 64 * 1024]

            return meta["mime_type"], meta["tts_provider"], cached_stream()

        text = await self._find_question_text(session_id, question_index)
        if not text:
            raise VoiceProviderException("Question text was not found")

        mime_type, provider, provider_stream = await self.voice.open_tts_stream(
            text,
            session.language,
        )
        await self.voice.set_tts_status(session_id, question_index, "streaming")

        async def cache_while_streaming():
            audio = bytearray()
            completed = False
            try:
                async for chunk in provider_stream:
                    if chunk:
                        audio.extend(chunk)
                        yield chunk
                completed = True
            finally:
                if completed and audio:
                    await self.voice.cache_tts(
                        session_id,
                        question_index,
                        bytes(audio),
                        mime_type=mime_type,
                        tts_provider=provider,
                        fallback_used=False,
                    )
                    await self.voice.set_tts_status(
                        session_id, question_index, "ready"
                    )
                    logger.info(
                        "Question TTS stream complete: session=%s q=%d provider=%s bytes=%d",
                        session_id,
                        question_index,
                        provider,
                        len(audio),
                    )

        return mime_type, provider, cache_while_streaming()

    async def _generate_question_tts_background(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: list[str] | None = None,
    ) -> None:
        started_at = time.perf_counter()
        await self.voice.set_tts_status(session_id, question_index, "pending")
        chunks = self._split_tts_chunks(text)
        concurrency = max(1, settings.TTS_BATCH_CONCURRENCY)
        logger.info(
            "Background TTS started: session=%s q=%d chunks=%d chars=%d concurrency=%d",
            session_id,
            question_index,
            len(chunks),
            len(text or ""),
            concurrency,
        )

        try:
            semaphore = asyncio.Semaphore(concurrency)

            async def synthesize_chunk(index: int, chunk: str) -> SynthesisResult:
                async with semaphore:
                    chunk_started = time.perf_counter()
                    result = await self.voice.text_to_speech(
                        chunk,
                        language,
                        hotwords=hotwords or [],
                    )
                    logger.info(
                        "Background TTS chunk complete: session=%s q=%d chunk=%d/%d elapsed=%.0fms bytes=%d",
                        session_id,
                        question_index,
                        index + 1,
                        len(chunks),
                        (time.perf_counter() - chunk_started) * 1000,
                        len(result.audio_bytes),
                    )
                    return result

            results = await asyncio.gather(
                *[
                    synthesize_chunk(index, chunk)
                    for index, chunk in enumerate(chunks)
                    if chunk.strip()
                ]
            )
            if not results:
                raise VoiceProviderException("No TTS chunks were generated")

            final_result = results[0] if len(results) == 1 else TTSAudioStitcher().stitch(results)
            await self.voice.cache_tts(
                session_id,
                question_index,
                final_result.audio_bytes,
                mime_type=final_result.mime_type,
                tts_provider=final_result.tts_provider,
                fallback_used=final_result.fallback_used,
            )
            await self.voice.set_tts_status(session_id, question_index, "ready")
            logger.info(
                "Background TTS ready: session=%s q=%d elapsed=%.0fms bytes=%d provider=%s",
                session_id,
                question_index,
                (time.perf_counter() - started_at) * 1000,
                len(final_result.audio_bytes),
                final_result.tts_provider,
            )
        except Exception as exc:
            await self.voice.set_tts_status(
                session_id,
                question_index,
                "failed",
                "tts_generation_failed",
            )
            logger.warning(
                "Background TTS failed: session=%s q=%d error=%s",
                session_id,
                question_index,
                exc,
            )

    async def _find_question_text(
        self, session_id: str, question_index: int
    ) -> str | None:
        history = await self.voice.get_history(session_id)
        assistant_turns = [
            entry.get("content", "")
            for entry in history
            if entry.get("role") == "assistant"
        ]
        if 1 <= question_index <= len(assistant_turns):
            return assistant_turns[question_index - 1]
        return None

    @staticmethod
    def _split_tts_chunks(text: str) -> list[str]:
        """Split long TTS text into bounded chunks without changing displayed text."""
        cleaned = re.sub(r"\s+", " ", (text or "").strip())
        if not cleaned:
            return []

        max_chars = max(80, settings.TTS_CHUNK_CHARS)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
        chunks: list[str] = []

        def append_piece(piece: str) -> None:
            piece = piece.strip()
            if not piece:
                return
            if not chunks or len(chunks[-1]) + len(piece) + 1 > max_chars:
                chunks.append(piece)
            else:
                chunks[-1] = f"{chunks[-1]} {piece}"

        for sentence in sentences or [cleaned]:
            if len(sentence) <= max_chars:
                append_piece(sentence)
                continue

            current = ""
            for word in sentence.split():
                if current and len(current) + len(word) + 1 > max_chars:
                    append_piece(current)
                    current = word
                else:
                    current = word if not current else f"{current} {word}"
            append_piece(current)

        return chunks

    def _finish_background_tts_task(self, task: asyncio.Task) -> None:
        self._pending_tts_tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            logger.exception("Background TTS task crashed: %s", exc)

    async def shutdown(self) -> None:
        """Cancel and drain background TTS work before dependencies close."""
        tasks = list(self._pending_tts_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._pending_tts_tasks.clear()

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

        raw_evaluation = evaluation_json if isinstance(evaluation_json, str) else ""
        try:
            return InterviewFeedback.model_validate_json(raw_evaluation)
        except (ValidationError, ValueError, TypeError):
            # Some providers wrap otherwise-valid JSON in prose or code fences.
            start = raw_evaluation.find("{")
            end = raw_evaluation.rfind("}")
            if start >= 0 and end > start:
                try:
                    return InterviewFeedback.model_validate_json(
                        raw_evaluation[start : end + 1]
                    )
                except (ValidationError, ValueError, TypeError):
                    pass
            logger.exception("LLM returned invalid interview feedback JSON")
            return InterviewFeedback(
                score=0,
                summary="Automated feedback is temporarily unavailable.",
                technical_skills=[],
                soft_skills=[],
                recommended_hire=False,
            )

    async def analyze_vetting(self, request: AnalyzeVettingRequest) -> InterviewFeedback:
        """Analyze candidate answers to vetting questions and calculate difficulty-weighted score."""
        qa_lines = []
        for pair in request.qa_pairs:
            qa_lines.append(
                f"[Question {pair.question_index}] ({pair.question_text})\n"
                f"Candidate Answer: {pair.candidate_answer}\n"
                "---------------------"
            )
        qa_block = "\n".join(qa_lines)

        job_title = request.job_title.strip()
        job_description = (request.job_description or "").strip()
        job_skills = ", ".join(request.job_skills) if request.job_skills else "Software Engineering"

        system_prompt = (
            "You are an expert technical recruiter and hiring manager evaluating a candidate's vetting questions and answers.\n"
            "Analyze the provided questions and candidate answers and produce a structured evaluation report.\n"
            "\n"
            "For each question-answer pair:\n"
            "1. Identify the Question Text.\n"
            "2. Classify the Question Type:\n"
            "   - \"theoretical\": Concepts, architecture, definitions.\n"
            "   - \"problem_solving\": Practical tasks, coding, debugging, scenario resolution.\n"
            "3. Classify the Question Difficulty:\n"
            "   - \"easy\": Basic conceptual queries or simple syntax.\n"
            "   - \"medium\": Standard scenarios, intermediate logic, or typical debugging.\n"
            "   - \"hard\": High-scale design, deep performance tuning, concurrency, or advanced algorithms.\n"
            "4. Extract the Candidate's Answer.\n"
            "5. Grade the Candidate's Answer (Score 0-100) using these strict guidelines:\n"
            "   - 90-100: Flawless, detailed, covers edge cases and best practices.\n"
            "   - 70-89: Solid correctness, competent, minor gaps.\n"
            "   - 50-69: Basic understanding, lacks detail, minor flaws.\n"
            "   - 1-49: Incorrect, major misconceptions.\n"
            "   - 0: Skipped, refused, or completely irrelevant.\n"
            "6. Provide a concise, recruiter-focused justification Feedback for this specific answer.\n"
            "\n"
            "Also, provide an overall evaluation:\n"
            "- Recommended Hire (true/false) based on whether they meet professional engineering standards.\n"
            "- Overall Summary of their performance, highlighting key strengths and areas of growth.\n"
            "- Assessed Technical Skills: List specific technologies/skills demonstrated.\n"
            "- Assessed Soft Skills: Communication quality, structural clarity, and confidence.\n"
            "- Holistic Adjustment: An integer value between -15 and +15 reflecting soft skills, deal-breakers, or exceptional performance not fully captured by raw question averages.\n"
            "- Holistic Adjustment Reason: Explaining why the adjustment was made.\n"
            "\n"
            "Output strictly in JSON according to the schema requested. Do not include markdown code fences (like ```json) or leading/trailing conversational text."
        )

        user_prompt = (
            "Evaluate the following candidate vetting answers from the recruiter's perspective:\n\n"
            f"Job Title: {job_title}\n"
            f"Job Description: {job_description}\n"
            f"Expected Skills: {job_skills}\n\n"
            "Vetting Questions & Answers:\n"
            f"{qa_block}"
        )

        evaluation_json = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=InterviewFeedback,
        )

        raw_evaluation = evaluation_json if isinstance(evaluation_json, str) else ""
        feedback = None
        try:
            feedback = InterviewFeedback.model_validate_json(raw_evaluation)
        except (ValidationError, ValueError, TypeError):
            # Fallback parsing for wrapped JSON
            start = raw_evaluation.find("{")
            end = raw_evaluation.rfind("}")
            if start >= 0 and end > start:
                try:
                    feedback = InterviewFeedback.model_validate_json(
                        raw_evaluation[start : end + 1]
                    )
                except (ValidationError, ValueError, TypeError):
                    pass

        if not feedback:
            logger.exception("LLM returned invalid vetting evaluation JSON")
            return InterviewFeedback(
                score=0,
                summary="Automated vetting feedback is temporarily unavailable.",
                technical_skills=[],
                soft_skills=[],
                recommended_hire=False,
                holistic_adjustment=0,
                holistic_adjustment_reason="Failed to parse AI response.",
                graded_questions=[],
            )

        # ── Calculate Programmatic Weighted Score ──────────────────
        difficulty_weights = {
            "easy": 1.0,
            "medium": 1.5,
            "hard": 2.0
        }

        total_weighted_score = 0.0
        total_weight = 0.0

        for gq in feedback.graded_questions:
            weight = difficulty_weights.get(gq.difficulty.lower(), 1.0)
            total_weighted_score += gq.score * weight
            total_weight += weight

        if total_weight > 0:
            base_score = total_weighted_score / total_weight
        else:
            base_score = 0.0

        final_score = int(round(base_score + feedback.holistic_adjustment))
        feedback.score = max(0, min(100, final_score))

        return feedback


# ── Dependency injection ────────────────────────────────────────

_interview_service: InterviewService | None = None
_interview_service_lock = None


async def get_interview_service() -> InterviewService:
    """Return an InterviewService with all dependencies wired.

    This replaces the old synchronous singleton with an async factory
    that awaits the VoiceService singleton initialization.
    """
    global _interview_service, _interview_service_lock
    if _interview_service is None:
        import asyncio

        if _interview_service_lock is None:
            _interview_service_lock = asyncio.Lock()
        async with _interview_service_lock:
            if _interview_service is None:
                llm = get_llm_gateway()
                voice = await get_voice_service()
                _interview_service = InterviewService(
                    llm_gateway=llm,
                    voice_service=voice,
                )
                logger.info("InterviewService singleton initialized")
    return _interview_service
