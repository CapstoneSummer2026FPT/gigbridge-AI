"""Voice Gateway — Chain of Responsibility for STT/TTS with fallback.

The gateway holds ALL known providers in priority order, built at init time.
It iterates through providers on each request, catching VoiceProviderException
from each and trying the next. This is the Chain of Responsibility pattern.

Design decisions:
  - Build ALL known providers upfront, skip ones that fail to init.
    This avoids the trap of STT_FALLBACK_PROVIDER="faster_whisper"
    silently having no fallback because the engine failed to init.
  - Every provider call is wrapped in asyncio.wait_for(timeout=30).
  - TimeoutError is treated the same as a provider failure — triggers fallback.
  - If ALL providers fail, raises VoiceProviderException with all error details.
"""

import asyncio
import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.models import TranscriptionResult, SynthesisResult
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.clients.voice.factories.stt_factory import STTFactory
from app.clients.voice.factories.tts_factory import TTSFactory
from app.clients.voice.session import VoiceSessionManager

logger = logging.getLogger("ai_server.voice.gateway")

# Default timeout for individual provider calls
_PROVIDER_TIMEOUT = 30.0


class VoiceGateway:
    """Gateway that orchestrates STT/TTS providers with automatic fallback.

    Usage:
        gateway = VoiceGateway()
        result = await gateway.transcribe_with_fallback(audio_bytes, "vi")
        result = await gateway.synthesize_with_fallback("Hello", "vi")
    """

    def __init__(self):
        # Build STT providers: try all known, skip failures
        self.stt_providers: list[tuple[str, BaseSTTEngine]] = []
        try:
            self.stt_providers = STTFactory.all_providers()
        except Exception as exc:
            logger.error("Failed to build STT providers: %s", exc)

        if not self.stt_providers:
            logger.critical("No STT providers could be initialized")
            raise VoiceProviderException("No STT providers available")

        # Build TTS providers: try all known, skip failures
        self.tts_providers: list[tuple[str, BaseTTSEngine]] = []
        try:
            self.tts_providers = TTSFactory.all_providers()
        except Exception as exc:
            logger.error("Failed to build TTS providers: %s", exc)

        if not self.tts_providers:
            logger.critical("No TTS providers could be initialized")
            raise VoiceProviderException("No TTS providers available")

        # Session manager (Redis-backed)
        self.session = VoiceSessionManager()

        logger.info(
            "VoiceGateway initialized: STT=%s, TTS=%s",
            [p[0] for p in self.stt_providers],
            [p[0] for p in self.tts_providers],
        )

    # ── Primary public methods ─────────────────────────────────

    async def transcribe_with_fallback(self, audio: bytes, language: str) -> TranscriptionResult:
        """Transcribe audio using the first available STT provider.

        Tries each provider in priority order. On failure, logs the error
        and tries the next provider. If all fail, raises VoiceProviderException.

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
            language: BCP-47 language hint ('vi' or 'en').

        Returns:
            TranscriptionResult with provider metadata set.

        Raises:
            VoiceProviderException: If ALL providers fail.
        """
        errors: list[str] = []
        primary_name = self.stt_providers[0][0]

        for name, provider in self.stt_providers:
            try:
                result = await asyncio.wait_for(
                    provider.transcribe(audio, language),
                    timeout=_PROVIDER_TIMEOUT,
                )
                result.stt_provider = name
                result.fallback_used = name != primary_name
                if result.fallback_used:
                    logger.info("STT fallback used: %s (primary=%s)", name, primary_name)
                return result
            except (VoiceProviderException, asyncio.TimeoutError) as exc:
                logger.warning("STT provider '%s' failed: %s", name, exc)
                errors.append(f"{name}: {exc}")
                continue

        raise VoiceProviderException(
            "All STT providers failed",
            errors=errors,
        )

    async def synthesize_with_fallback(self, text: str, language: str) -> SynthesisResult:
        """Synthesize speech using the first available TTS provider.

        Args:
            text: Text to vocalize.
            language: BCP-47 language code ('vi' or 'en') for voice selection.

        Returns:
            SynthesisResult with provider metadata set.

        Raises:
            VoiceProviderException: If ALL providers fail.
        """
        errors: list[str] = []
        primary_name = self.tts_providers[0][0]

        for name, provider in self.tts_providers:
            try:
                result = await asyncio.wait_for(
                    provider.synthesize(text, language),
                    timeout=_PROVIDER_TIMEOUT,
                )
                result.tts_provider = name
                result.fallback_used = name != primary_name
                if result.fallback_used:
                    logger.info("TTS fallback used: %s (primary=%s)", name, primary_name)
                return result
            except (VoiceProviderException, asyncio.TimeoutError) as exc:
                logger.warning("TTS provider '%s' failed: %s", name, exc)
                errors.append(f"{name}: {exc}")
                continue

        raise VoiceProviderException(
            "All TTS providers failed",
            errors=errors,
        )
