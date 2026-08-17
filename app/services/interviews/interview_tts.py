"""
PURPOSE: Text-to-Speech audio generation, background scheduling, polling, and streaming endpoint handler for voice interviews.
IMPORTANCE: High — Manages voice synthesis playback streams and TTS caching in Redis.
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_tts.py -> app/api/routes/interviews.py
"""

import asyncio
import base64
import logging
from typing import Dict, List, Optional, Set, Tuple

from app.core.exceptions import (
    SessionAccessDeniedError,
    SessionExpiredError,
    VoiceProviderException,
)
from app.services.interviews.interview_base import InterviewBaseService

logger = logging.getLogger("ai_server.interview_tts")


class InterviewTTSService(InterviewBaseService):
    """Handles Text-to-Speech audio synthesis background scheduling, caching, and audio streaming."""

    def __init__(self, *args, **kwargs):
        """Initialize InterviewTTSService with tracking set for background tasks."""
        super().__init__(*args, **kwargs)
        self._pending_tts_tasks: Set[asyncio.Task] = set()

    async def schedule_question_tts(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: Optional[List[str]] = None,
    ) -> None:
        """Schedule asynchronous background TTS generation for an interview question text.
        
        Flow:
        1. Check if audio is already cached in Redis for this session & index.
        2. Check current TTS status in Redis (return if pending/ready).
        3. Set TTS status to 'pending' and spawn asyncio background task.
        4. Track background task in self._pending_tts_tasks with done callback.
        """
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
        """Poll cached TTS question audio or return current background synthesis status.
        
        Flow:
        1. Verify audio access token against session hash in Redis.
        2. Load session from Redis (fail fast if expired).
        3. Check Redis TTS cache; return base64 encoded audio payload if ready.
        4. If missing, retrieve question text and schedule background synthesis.
        5. Return status dictionary (status='pending'|'ready'|'failed'|'missing').
        """
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
    ) -> Tuple[str, str, any]:
        """Open immediate single-voice TTS audio stream for an interview question.
        
        Flow:
        1. Verify audio access token against session hash.
        2. Load session from Redis.
        3. If audio is cached in Redis, yield chunks from cached byte array.
        4. If not cached, retrieve question text and open live TTS stream via VoiceService.
        5. Stream chunks while caching synthesized audio bytes into Redis in background.
        """
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
                        session_id, question_index, provider, len(audio),
                    )

        return mime_type, provider, cache_while_streaming()

    async def _generate_question_tts_background(
        self,
        session_id: str,
        question_index: int,
        text: str,
        language: str,
        hotwords: List[str],
    ) -> None:
        """Background coroutine that synthesizes TTS audio and caches it in Redis."""
        try:
            result = await self.voice.text_to_speech(
                text,
                language=language,
                hotwords=hotwords,
            )
            await self.voice.cache_tts(
                session_id,
                question_index,
                result.audio_bytes,
                mime_type=result.mime_type,
                tts_provider=result.tts_provider,
                fallback_used=result.fallback_used,
            )
            await self.voice.set_tts_status(session_id, question_index, "ready")
            logger.info(
                "Background TTS complete: session=%s q=%d provider=%s bytes=%d",
                session_id, question_index, result.tts_provider, len(result.audio_bytes),
            )
        except Exception as exc:
            logger.error(
                "Background TTS failed: session=%s q=%d err=%s",
                session_id, question_index, str(exc),
            )
            await self.voice.set_tts_status(
                session_id, question_index, "failed", "tts_generation_failed"
            )

    async def _find_question_text(
        self, session_id: str, question_index: int
    ) -> Optional[str]:
        """Find question text in Redis conversation history by question index."""
        history = await self.voice.get_history(session_id)
        assistant_messages = [
            msg["content"] for msg in history if msg.get("role") == "assistant"
        ]
        if 1 <= question_index <= len(assistant_messages):
            return assistant_messages[question_index - 1]
        return None

    def _finish_background_tts_task(self, task: asyncio.Task) -> None:
        """Discard finished asyncio task from tracking set."""
        self._pending_tts_tasks.discard(task)
