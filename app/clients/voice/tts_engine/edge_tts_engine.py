"""Edge TTS engine — PRIMARY free TTS provider.

Uses Microsoft Edge's online TTS API (edge-tts library).
Zero cost, excellent Vietnamese voice (vi-VN-HoaiMyNeural).
Falls back on timeout (5s) or network error.

CRITICAL: edge_tts.Communicate.stream() is an ASYNC GENERATOR, not a coroutine.
We collect chunks in an inner _collect() function and wrap that with wait_for.
"""

import asyncio
import logging

import edge_tts

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.clients.voice.models import SynthesisResult

logger = logging.getLogger("ai_server.voice.edge_tts")

# Language -> (edge-tts voice name)
_VOICE_MAP = {
    "vi": settings.EDGE_TTS_VOICE_VI or "vi-VN-HoaiMyNeural",
    "en": settings.EDGE_TTS_VOICE_EN or "en-US-JennyNeural",
}


class EdgeTTSEngine(BaseTTSEngine):
    """Edge TTS engine using Microsoft's online neural voices.

    Completely free, no API key required. Excellent Vietnamese support.
    """

    async def synthesize(self, text: str, language: str) -> SynthesisResult:
        """Synthesize text to MP3 audio via edge-tts.

        Collects chunks from the async generator before applying the timeout,
        ensuring we return complete audio bytes.
        """
        voice = _VOICE_MAP.get(language, _VOICE_MAP["vi"])
        communicate = edge_tts.Communicate(text, voice)

        async def _collect() -> bytes:
            """Iterate the async generator and collect all audio chunks."""
            audio = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
            return bytes(audio)

        try:
            audio_bytes = await asyncio.wait_for(
                _collect(), timeout=settings.EDGE_TTS_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise VoiceProviderException(
                f"Edge TTS timed out after {settings.EDGE_TTS_TIMEOUT}s"
            )
        except Exception as exc:
            raise VoiceProviderException(f"Edge TTS failed: {exc}")

        if not audio_bytes:
            raise VoiceProviderException("Edge TTS returned empty audio")

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/mpeg",
            tts_provider="edge_tts",
        )
