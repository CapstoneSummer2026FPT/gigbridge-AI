"""
PURPOSE: Unified facade module for stateful voice and text AI candidate interviews.
IMPORTANCE: Critical — Primary entrypoint for interview domain services across API routes and test suites.
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_session.py -> app/services/interviews/interview_stt.py -> app/services/interviews/interview_tts.py -> app/services/interviews/interview_judgement.py -> app/services/interviews/__init__.py
"""

import asyncio
import logging
from typing import Optional

from app.schemas.interviews import (
    AnalyzeVettingRequest,
    DraftDataResponse,
    InterviewFeedback,
    InterviewQuestionResponse,
    StartInterviewRequest,
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.audio.voice import VoiceService, get_voice_service
from app.services.rag.hotword_resolver import HotwordResolver, get_hotword_resolver
from app.services.interviews.interview_base import InterviewBaseService
from app.services.interviews.interview_session import InterviewSessionService
from app.services.interviews.interview_stt import InterviewSTTService
from app.services.interviews.interview_tts import InterviewTTSService
from app.services.interviews.interview_judgement import InterviewJudgementService
from app.services.interviews.transcript_corrector import TranscriptCorrector

logger = logging.getLogger("ai_server.interviews_facade")


class InterviewService(InterviewBaseService):
    """Facade class composing InterviewSessionService, InterviewSTTService, InterviewTTSService, and InterviewJudgementService."""

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        voice_service: Optional[VoiceService] = None,
        hotword_resolver: Optional[HotwordResolver] = None,
    ):
        """Initialize InterviewService facade with sub-service delegates."""
        super().__init__(
            llm_gateway=llm_gateway,
            voice_service=voice_service,
            hotword_resolver=hotword_resolver,
        )
        self.session_service = InterviewSessionService(
            llm_gateway=self.llm,
            voice_service=self.voice,
            hotword_resolver=self.hotword_resolver,
        )
        self.stt_service = InterviewSTTService(
            llm_gateway=self.llm,
            voice_service=self.voice,
            hotword_resolver=self.hotword_resolver,
        )
        self.tts_service = InterviewTTSService(
            llm_gateway=self.llm,
            voice_service=self.voice,
            hotword_resolver=self.hotword_resolver,
        )
        self.judgement_service = InterviewJudgementService(
            llm_gateway=self.llm,
            voice_service=self.voice,
            hotword_resolver=self.hotword_resolver,
        )
        self.transcript_corrector = TranscriptCorrector()

    async def initialize_interview(
        self, request: StartInterviewRequest
    ) -> InterviewQuestionResponse:
        """Delegate session initialization."""
        return await self.session_service.initialize_interview(request)

    async def process_answer(
        self, session_id: str, answer_text: str
    ) -> InterviewQuestionResponse:
        """Delegate text-mode answer processing."""
        return await self.session_service.process_answer(
            session_id, answer_text, feedback_generator=self.judgement_service.generate_feedback
        )

    async def transcribe_audio(
        self, session_id: str, pcm_wav_bytes: bytes, language: str | None = None
    ) -> DraftDataResponse:
        """Delegate audio transcription."""
        return await self.stt_service.transcribe_audio(session_id, pcm_wav_bytes, language=language)

    async def confirm_answer(
        self, session_id: str, corrected_text: str | None = None
    ) -> InterviewQuestionResponse:
        """Delegate atomic answer confirmation."""
        return await self.stt_service.confirm_answer(
            session_id,
            corrected_text=corrected_text,
            question_generator=self.session_service.generate_next_question,
            feedback_generator=self.judgement_service.generate_feedback,
        )

    @property
    def _pending_tts_tasks(self):
        """Property returning pending TTS background tasks set from tts_service."""
        return self.tts_service._pending_tts_tasks

    async def _generate_question_tts_background(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: list[str] | None = None,
    ) -> None:
        """Delegate background TTS generation to tts_service."""
        return await self.tts_service._generate_question_tts_background(
            session_id, question_index, text, language, hotwords=hotwords
        )

    async def schedule_question_tts(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: list[str] | None = None,
    ) -> None:
        """Delegate TTS background scheduling."""
        return await self.tts_service.schedule_question_tts(
            session_id, question_index, text, language, hotwords=hotwords
        )

    async def get_question_audio(
        self, session_id: str, question_index: int, audio_access_token: str
    ) -> dict:
        """Delegate TTS question audio polling."""
        return await self.tts_service.get_question_audio(
            session_id, question_index, audio_access_token
        )

    async def stream_question_audio(
        self,
        session_id: str,
        question_index: int,
        audio_access_token: str,
    ):
        """Delegate TTS question audio streaming."""
        return await self.tts_service.stream_question_audio(
            session_id, question_index, audio_access_token
        )

    async def _generate_feedback(self, session_id: str) -> InterviewFeedback:
        """Delegate feedback generation for backward compatibility."""
        return await self.judgement_service.generate_feedback(session_id)

    async def analyze_vetting(self, request: AnalyzeVettingRequest) -> InterviewFeedback:
        """Delegate candidate vetting analysis."""
        return await self.judgement_service.analyze_vetting(request)


_interview_service: Optional[InterviewService] = None
_interview_service_lock = None


async def get_interview_service() -> InterviewService:
    """Async singleton dependency injection helper for InterviewService."""
    global _interview_service, _interview_service_lock
    if _interview_service is None:
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
