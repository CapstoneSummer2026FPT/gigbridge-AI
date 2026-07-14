"""Google Cloud Text-to-Speech engine — async, fallback TTS provider.

Uses TextToSpeechAsyncClient. WaveNet voice for Vietnamese, standard for English.
Falls back to Standard voice if WaveNet quota is exhausted.
"""

import asyncio
import logging

# Google SDK imports are LAZY — inside _get_client() / synthesize() below.

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.clients.voice.models import SynthesisResult

logger = logging.getLogger("ai_server.voice.google_tts")

# Language -> (WaveNet voice, Standard fallback)
_VOICE_MAP = {
    "vi": ("vi-VN-Wavenet-A", "vi-VN-Standard-A"),
    "en": ("en-US-Wavenet-D", "en-US-Standard-D"),
}


class GoogleTTSEngine(BaseTTSEngine):
    """Google Cloud Text-to-Speech engine using the async client.

    Requires GOOGLE_APPLICATION_CREDENTIALS. Raises immediately if missing.
    """

    def __init__(self):
        if not settings.GOOGLE_APPLICATION_CREDENTIALS:
            raise VoiceProviderException(
                "GOOGLE_APPLICATION_CREDENTIALS not configured"
            )
        self._client = None

    async def _get_client(self):
        """Lazy-init the client. Google SDK imports are deferred."""
        if self._client is not None:
            return self._client
        from google.cloud.texttospeech import TextToSpeechAsyncClient

        self._client = TextToSpeechAsyncClient()
        return self._client

    async def synthesize(self, text: str, language: str) -> SynthesisResult:
        """Synthesize text to MP3 audio via Google Cloud TTS (async).

        Args:
            text: Text to vocalize.
            language: BCP-47 code ('vi' or 'en').

        Returns:
            SynthesisResult with MP3 audio bytes.

        Raises:
            VoiceProviderException: On API error, quota, or missing credentials.
        """
        from google.cloud.texttospeech import (
            SynthesisInput,
            VoiceSelectionParams,
            AudioConfig,
            AudioEncoding,
            SsmlVoiceGender,
        )

        client = await self._get_client()
        voices = _VOICE_MAP.get(language, _VOICE_MAP["vi"])
        bcp47 = {"vi": "vi-VN", "en": "en-US"}.get(language, "vi-VN")

        synthesis_input = SynthesisInput(text=text)

        # Try WaveNet first, fall back to Standard
        for voice_name in voices:
            voice = VoiceSelectionParams(
                language_code=bcp47,
                name=voice_name,
                ssml_gender=SsmlVoiceGender.NEUTRAL,
            )
            audio_config = AudioConfig(audio_encoding=AudioEncoding.MP3)

            try:
                response = await asyncio.wait_for(
                    client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config,
                    ),
                    timeout=settings.TTS_PROVIDER_TIMEOUT,
                )
                if response.audio_content:
                    return SynthesisResult(
                        audio_bytes=response.audio_content,
                        mime_type="audio/mpeg",
                        tts_provider="google_tts",
                    )
            except asyncio.TimeoutError:
                logger.warning(f"Google TTS {voice_name} timed out")
                continue  # try fallback voice
            except Exception as exc:
                logger.warning(f"Google TTS {voice_name} failed: {exc}")
                continue  # try fallback voice

        raise VoiceProviderException("Google TTS failed — all voices exhausted")
