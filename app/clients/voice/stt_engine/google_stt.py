"""Google Cloud Speech-to-Text engine — async, PRIMARY for Render deployment.

Uses SpeechAsyncClient to avoid blocking the event loop.
Receives pre-decoded WAV 16kHz mono PCM (LINEAR16 encoding).
No WEBM_OPUS format issues because the AudioProcessor decodes everything to WAV first.
"""

import asyncio
import logging
from typing import Optional

# Google SDK imports are LAZY — inside _get_client() / transcribe() below.
# This means importing this module does NOT require google-cloud-speech installed.
# The error only surfaces when someone tries to actually USE the engine.

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.clients.voice.models import TranscriptionResult

logger = logging.getLogger("ai_server.voice.google_stt")

# Language map: internal short code -> BCP-47 for Google API
_LANGUAGE_MAP = {
    "vi": "vi-VN",
    "vi-VN": "vi-VN",
    "vi-vn": "vi-VN",
    "en": "en-US",
    "en-US": "en-US",
    "en-us": "en-US",
}


class GoogleSTTEngine(BaseSTTEngine):
    """Google Cloud Speech-to-Text engine using the async client.

    Requires GOOGLE_APPLICATION_CREDENTIALS to be set in environment.
    Raises VoiceProviderException immediately if no credentials are configured
    (fail fast, not a fake result).
    """

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """Lazy-init the client. Google SDK imports are deferred so importing
        this module works without google-cloud-speech installed."""
        if self._client is not None:
            return self._client
        if not settings.GOOGLE_APPLICATION_CREDENTIALS:
            raise VoiceProviderException(
                "GOOGLE_APPLICATION_CREDENTIALS not configured"
            )
        # Lazy import: google-cloud-speech may not be installed
        from google.cloud.speech import SpeechAsyncClient

        self._client = SpeechAsyncClient()
        return self._client

    async def transcribe(
        self,
        audio: bytes,
        language: str,
        hotwords: Optional[list[str]] = None,
        primary_language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe WAV PCM audio via Google Cloud STT (async).

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
            language: BCP-47 hint ('vi', 'en') or 'auto'/'mixed'.
            hotwords: Optional job-specific words for speech context biasing.
            primary_language: Session primary language used when language is auto/mixed.

        Returns:
            TranscriptionResult with confidence score from Google.

        Raises:
            VoiceProviderException: On quota exhaustion, API error, timeout,
                                    or missing credentials.
        """
        # Lazy imports for Google types (inside method, not module level)
        from google.cloud.speech import RecognitionConfig, RecognitionAudio, SpeechContext

        client = await self._get_client()
        requested = (language or "").strip().lower()
        primary_hint = (primary_language or requested or "vi").strip()
        bcp47 = _LANGUAGE_MAP.get(primary_hint, _LANGUAGE_MAP.get(primary_hint[:2], "vi-VN"))
        alt = "en-US" if bcp47 == "vi-VN" else "vi-VN"

        speech_contexts = []
        cleaned_hotwords = [word.strip() for word in (hotwords or []) if word and word.strip()]
        if cleaned_hotwords:
            speech_contexts.append(
                SpeechContext(
                    phrases=cleaned_hotwords,
                    boost=settings.GOOGLE_STT_HOTWORD_BOOST,
                )
            )

        config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=bcp47,
            alternative_language_codes=[alt] if requested in {"auto", "mixed"} else [],
            enable_automatic_punctuation=True,
            speech_contexts=speech_contexts,
            model="default",
        )
        recognition_audio = RecognitionAudio(content=audio)

        try:
            response = await asyncio.wait_for(
                client.recognize(config=config, audio=recognition_audio),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            raise VoiceProviderException("Google STT timed out after 30s")
        except Exception as exc:
            raise VoiceProviderException(f"Google STT failed: {exc}")

        if not response.results:
            raise VoiceProviderException("Google STT returned empty results")

        best = response.results[0].alternatives[0]
        confidence = best.confidence if best.confidence is not None else 0.0

        return TranscriptionResult(
            text=best.transcript,
            language=bcp47,
            confidence=confidence,
            stt_provider="google_stt",
        )
