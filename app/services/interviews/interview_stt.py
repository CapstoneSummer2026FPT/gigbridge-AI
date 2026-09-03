"""
PURPOSE: Speech-to-Text transcription and atomic draft confirmation workflows for voice interview answers.
IMPORTANCE: Critical — Primary audio processing layer handling candidate speech transcription, draft verification, and answer confirmation.
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_stt.py -> app/api/routes/interviews.py
"""

import datetime
from datetime import timezone, timedelta
import logging
import time
import uuid

from app.schemas.interviews import (
    DraftDataResponse,
    InterviewQuestionResponse,
)
from app.core.config import settings
from app.core.exceptions import (
    ConfirmConflictError,
    DraftExpiredError,
    InvalidAnswerError,
    SessionExpiredError,
)
from app.clients.voice.models import DraftData
from app.services.interviews.interview_base import InterviewBaseService
from app.services.interviews.transcript_corrector import TranscriptCorrector

logger = logging.getLogger("ai_server.interview_stt")


class InterviewSTTService(InterviewBaseService):
    """Handles speech-to-text audio transcription and atomic draft answer confirmation."""

    def __init__(self, *args, **kwargs):
        """Initialize InterviewSTTService with transcript corrector."""
        super().__init__(*args, **kwargs)
        self.transcript_corrector = TranscriptCorrector()

    async def transcribe_audio(
        self, session_id: str, pcm_wav_bytes: bytes, language: str | None = None
    ) -> DraftDataResponse:
        """Transcribe PCM WAV audio bytes and save temporary draft (Step 1 of atomic confirm).
        
        Flow:
        1. Load session from Redis (fail fast if expired).
        2. Execute STT speech-to-text with fallback handling.
        3. Apply local transcript correction (hotwords & phonetic aliases).
        4. Create DraftData object and save to Redis with draft TTL.
        5. Return DraftDataResponse.
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
            created_at=datetime.datetime.now(timezone.utc).isoformat(),
        )
        save_started = time.perf_counter()
        await self.voice.save_draft(session_id, draft)
        save_ms = (time.perf_counter() - save_started) * 1000

        expires_at = (
            datetime.datetime.now(timezone.utc) + timedelta(seconds=settings.REDIS_DRAFT_TTL)
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
            "Interview transcribe timing: session=%s total=%.0fms load=%.0fms stt=%.0fms corr=%.0fms save=%.0fms provider=%s",
            session_id, total_ms, load_ms, stt_ms, correction_ms, save_ms, result.stt_provider,
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

    async def confirm_answer(
        self, session_id: str, corrected_text: str | None = None, question_generator=None, feedback_generator=None
    ) -> InterviewQuestionResponse:
        """Atomically consume draft answer and advance interview session (Step 2 of atomic confirm).
        
        Flow:
        1. Validate non-blank corrected text.
        2. Load session from Redis (fail fast if expired).
        3. Atomically consume draft via Redis GETDEL (prevents double-confirm).
        4. Save final answer to Redis conversation history and mark confirmed.
        5. Check if interview is complete -> generate feedback if complete.
        6. Otherwise, generate next question text, advance question pointer, and return.
        """
        if corrected_text is not None and not corrected_text.strip():
            corrected_text = "[No answer provided]"
        started_at = time.perf_counter()
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        draft = await self.voice.consume_draft(session_id)
        if not draft:
            if await self.voice.is_confirmed(session_id, session.question_index):
                raise ConfirmConflictError()
            fallback_text = (corrected_text or "").strip() or "[No answer provided]"
            draft = DraftData(
                draft_id=f"draft_fallback_{uuid.uuid4().hex}",
                question_index=session.question_index,
                transcript=fallback_text,
                language=session.language,
                stt_provider="fallback",
                confidence=1.0,
                created_at=datetime.datetime.now(timezone.utc).isoformat(),
            )

        final_answer = (corrected_text or draft.transcript).strip() or "[No answer provided]"

        await self.voice.add_history(
            session_id, "user", final_answer, draft.language
        )
        await self.voice.mark_confirmed(session_id, session.question_index)

        question_count = len(session.job_questions) or session.question_count
        is_complete = session.question_index >= question_count

        if is_complete:
            feedback = None
            if feedback_generator:
                feedback = await feedback_generator(session_id)
            total_ms = (time.perf_counter() - started_at) * 1000
            logger.info("Interview complete: session=%s total=%.0fms", session_id, total_ms)
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                question_count=question_count,
                is_completed=True,
                feedback=feedback,
                job_id=session.job_id,
                freelancer_id=session.freelancer_id,
            )

        next_index = session.question_index + 1
        history = await self.voice.get_history(session_id)
        if session.job_questions:
            next_question = session.job_questions[session.question_index]
        elif question_generator:
            next_question = await question_generator(history, session.language)
        else:
            next_question = "Please describe your relevant experience for this requirement."

        tts_provider = "streaming" if session.mode == "voice" else None
        await self.voice.advance_pointer(session_id)

        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )

        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Confirm advance: session=%s q=%d->%d total=%.0fms",
            session_id, session.question_index, next_index, total_ms,
        )

        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_count=question_count,
            question_text=next_question,
            language=session.language,
            audio_base64=None,
            audio_mime_type=None,
            tts_provider=tts_provider,
            fallback_used=False,
            is_completed=False,
            job_id=session.job_id,
            freelancer_id=session.freelancer_id,
        )
