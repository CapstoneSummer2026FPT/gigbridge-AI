"""VoiceService — Facade over the voice subsystem.

Provides a clean, high-level API for all voice operations:
  - speech_to_text() / text_to_speech() — delegates to gateway with fallback
  - Session lifecycle: create_session(), load_session(), delete_session()
  - Draft management: save_draft(), consume_draft()
  - TTS caching: cache_tts(), get_cached_tts()
  - Conversation history: add_history(), get_history()
  - Pointer advancement: advance_pointer()

Dependency injection: singleton with lazy init. The singleton is safe for
single-worker deployments. For multi-worker, replace with a factory.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.clients.voice.models import (
    TranscriptionResult,
    SynthesisResult,
    DraftData,
    InterviewSession,
)
from app.clients.voice.gateway import VoiceGateway

logger = logging.getLogger("ai_server.voice_service")


class VoiceService:
    """High-level facade over the voice subsystem.

    Holds the gateway (providers + session manager) and exposes
    a clean API for the interview service and API routes.
    """

    def __init__(self, gateway: Optional[VoiceGateway] = None):
        self.gateway = gateway or VoiceGateway()

    # ── Core STT/TTS ───────────────────────────────────────────

    async def speech_to_text(self, audio: bytes, language: str) -> TranscriptionResult:
        """Transcribe audio to text with automatic provider fallback.

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
            language: BCP-47 hint ('vi' or 'en').

        Returns:
            TranscriptionResult with provider metadata.
        """
        return await self.gateway.transcribe_with_fallback(audio, language)

    async def text_to_speech(self, text: str, language: str) -> SynthesisResult:
        """Synthesize text to speech audio with automatic provider fallback.

        Args:
            text: Text to vocalize.
            language: BCP-47 code for voice selection.

        Returns:
            SynthesisResult with audio bytes and metadata.
        """
        return await self.gateway.synthesize_with_fallback(text, language)

    # ── Session Management ─────────────────────────────────────

    async def create_session(self, session_data: dict) -> InterviewSession:
        """Create a new voice interview session in Redis."""
        return await self.gateway.session.create_session(session_data)

    async def load_session(self, session_id: str) -> Optional[InterviewSession]:
        """Load a session if it exists and hasn't expired."""
        return await self.gateway.session.load_or_expire(session_id)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all associated data."""
        await self.gateway.session.delete_session(session_id)

    # ── Draft Management ───────────────────────────────────────

    async def save_draft(self, session_id: str, draft: DraftData) -> None:
        """Save a transcription draft (10-minute TTL)."""
        await self.gateway.session.save_draft(session_id, draft)

    async def consume_draft(self, session_id: str) -> Optional[DraftData]:
        """Atomically consume a draft via GETDEL.

        Returns None if the draft was already consumed or expired.
        """
        return await self.gateway.session.consume_draft(session_id)

    # ── TTS Cache ──────────────────────────────────────────────

    async def cache_tts(self, session_id: str, question_index: int, audio_bytes: bytes) -> None:
        """Cache TTS audio for a question (15-minute TTL)."""
        await self.gateway.session.cache_tts(session_id, question_index, audio_bytes)

    async def get_cached_tts(self, session_id: str, question_index: int) -> Optional[bytes]:
        """Retrieve cached TTS audio, or None if not cached."""
        return await self.gateway.session.get_cached_tts(session_id, question_index)

    # ── Pointer Advancement ────────────────────────────────────

    async def advance_pointer(self, session_id: str) -> int:
        """Atomically increment the question index.

        Returns the new question index.
        """
        return await self.gateway.session.advance_pointer(session_id)

    # ── Confirm tracking ──────────────────────────────────────

    async def mark_confirmed(self, session_id: str) -> None:
        """Mark a session as having a confirmed answer."""
        await self.gateway.session.mark_confirmed(session_id)

    async def is_confirmed(self, session_id: str) -> bool:
        """Check if this session already has a confirmed answer."""
        return await self.gateway.session.is_confirmed(session_id)

    # ── Conversation History ───────────────────────────────────

    async def add_history(self, session_id: str, role: str, content: str, language: str) -> None:
        """Append a conversation turn to Redis history."""
        await self.gateway.session.add_history(session_id, role, content, language)

    async def get_history(self, session_id: str) -> list[dict]:
        """Retrieve full conversation history."""
        return await self.gateway.session.get_history(session_id)


# ── Dependency injection ────────────────────────────────────────

_voice_service: Optional[VoiceService] = None
_voice_service_lock = asyncio.Lock()


async def get_voice_service() -> VoiceService:
    """Return a singleton VoiceService with lazy initialization.

    Uses an asyncio.Lock to prevent duplicate initialization races
    at startup. Safe for single-worker deployments.
    """
    global _voice_service
    if _voice_service is None:
        async with _voice_service_lock:
            if _voice_service is None:
                gateway = VoiceGateway()
                _voice_service = VoiceService(gateway=gateway)
                logger.info("VoiceService singleton initialized")
    return _voice_service
