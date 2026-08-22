"""
PURPOSE: High-level VoiceService facade over speech-to-text, text-to-speech, and Redis session lifecycle.
IMPORTANCE: Critical — Primary voice integration service driving audio interviews and voice synthesis playback.
READING FLOW: app/services/audio/audio_processor.py -> app/services/audio/voice.py -> app/services/interviews/interview_base.py
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Optional

from app.clients.voice.models import (
    TranscriptionResult,
    SynthesisResult,
    DraftData,
    InterviewSession,
)
from app.clients.voice.gateway import VoiceGateway

logger = logging.getLogger("ai_server.voice_service")


class VoiceService:
    """High-level facade over speech-to-text, text-to-speech, and Redis session operations."""

    def __init__(self, gateway: Optional[VoiceGateway] = None):
        """Initialize VoiceService facade with VoiceGateway."""
        self.gateway = gateway or VoiceGateway()

    # ── Core STT/TTS ───────────────────────────────────────────

    async def speech_to_text(
        self,
        audio: bytes,
        language: str,
        hotwords: Optional[list[str]] = None,
        primary_language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe PCM WAV audio to text with automatic provider fallback."""
        return await self.gateway.transcribe_with_fallback(
            audio,
            language,
            hotwords=hotwords,
            primary_language=primary_language,
        )

    async def text_to_speech(
        self,
        text: str,
        language: str,
        hotwords: Optional[list[str]] = None,
    ) -> SynthesisResult:
        """Synthesize text to speech audio with automatic provider fallback."""
        return await self.gateway.synthesize_with_fallback(
            text,
            language,
            hotwords=hotwords,
        )

    async def open_tts_stream(
        self,
        text: str,
        language: str,
    ) -> tuple[str, str, AsyncIterator[bytes]]:
        """Open single-voice stream for immediate browser playback."""
        return await self.gateway.open_single_voice_stream(text, language)

    # ── Session Management ─────────────────────────────────────

    async def create_session(self, session_data: dict) -> InterviewSession:
        """Create new voice interview session in Redis."""
        return await self.gateway.session.create_session(session_data)

    async def load_session(self, session_id: str) -> Optional[InterviewSession]:
        """Load session data from Redis if non-expired."""
        return await self.gateway.session.load_or_expire(session_id)

    async def delete_session(self, session_id: str) -> None:
        """Delete session and associated data from Redis."""
        await self.gateway.session.delete_session(session_id)

    # ── Draft Management ───────────────────────────────────────

    async def save_draft(self, session_id: str, draft: DraftData) -> None:
        """Save transcription draft to Redis."""
        await self.gateway.session.save_draft(session_id, draft)

    async def consume_draft(self, session_id: str) -> Optional[DraftData]:
        """Atomically consume transcription draft via Redis GETDEL."""
        return await self.gateway.session.consume_draft(session_id)

    # ── TTS Cache ──────────────────────────────────────────────

    async def cache_tts(
        self,
        session_id: str,
        question_index: int,
        audio_bytes: bytes,
        mime_type: str = "audio/wav",
        tts_provider: str = "",
        fallback_used: bool = False,
    ) -> None:
        """Cache synthesized TTS question audio in Redis."""
        await self.gateway.session.cache_tts(
            session_id,
            question_index,
            audio_bytes,
            mime_type=mime_type,
            tts_provider=tts_provider,
            fallback_used=fallback_used,
        )

    async def get_cached_tts(self, session_id: str, question_index: int) -> Optional[bytes]:
        """Retrieve cached TTS audio from Redis."""
        return await self.gateway.session.get_cached_tts(session_id, question_index)

    async def get_cached_tts_meta(self, session_id: str, question_index: int) -> dict:
        """Retrieve cached TTS metadata from Redis."""
        return await self.gateway.session.get_cached_tts_meta(session_id, question_index)

    async def set_tts_status(
        self,
        session_id: str,
        question_index: int,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Store background TTS synthesis status in Redis."""
        await self.gateway.session.set_tts_status(
            session_id,
            question_index,
            status,
            error,
        )

    async def get_tts_status(self, session_id: str, question_index: int) -> dict:
        """Retrieve background TTS status from Redis."""
        return await self.gateway.session.get_tts_status(session_id, question_index)

    # ── Pointer Advancement ────────────────────────────────────

    async def advance_pointer(self, session_id: str) -> int:
        """Atomically increment question index pointer in Redis."""
        return await self.gateway.session.advance_pointer(session_id)

    # ── Confirm tracking ──────────────────────────────────────

    async def mark_confirmed(self, session_id: str) -> None:
        """Mark session as having a confirmed answer in Redis."""
        await self.gateway.session.mark_confirmed(session_id)

    async def is_confirmed(self, session_id: str) -> bool:
        """Check if session already has a confirmed answer in Redis."""
        return await self.gateway.session.is_confirmed(session_id)

    async def verify_audio_access_token(self, session_id: str, token: str) -> bool:
        """Verify authorization token for session TTS audio playback."""
        return await self.gateway.session.verify_audio_access_token(session_id, token)

    # ── Conversation History ───────────────────────────────────

    async def add_history(self, session_id: str, role: str, content: str, language: str) -> None:
        """Append conversation turn to Redis history."""
        await self.gateway.session.add_history(session_id, role, content, language)

    async def get_history(self, session_id: str) -> list[dict]:
        """Retrieve full conversation history from Redis."""
        return await self.gateway.session.get_history(session_id)


_voice_service: Optional[VoiceService] = None
_voice_service_lock: Optional[asyncio.Lock] = None


async def get_voice_service() -> VoiceService:
    """Dependency injection helper returning singleton instance of VoiceService."""
    global _voice_service, _voice_service_lock
    if _voice_service is None:
        if _voice_service_lock is None:
            _voice_service_lock = asyncio.Lock()
        async with _voice_service_lock:
            if _voice_service is None:
                gateway = VoiceGateway()
                _voice_service = VoiceService(gateway=gateway)
                logger.info("VoiceService singleton initialized")
    return _voice_service
