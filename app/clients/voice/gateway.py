"""Voice Gateway — Chain of Responsibility for STT/TTS with fallback.

The gateway holds ALL known providers in priority order, built at init time.
It iterates through providers on each request, catching VoiceProviderException
from each and trying the next. This is the Chain of Responsibility pattern.

Design decisions:
  - Build ALL known providers upfront, skip ones that fail to init.
    This avoids the trap of STT_FALLBACK_PROVIDER="faster_whisper"
    silently having no fallback because the engine failed to init.
  - Every provider call is wrapped in asyncio.wait_for using configured timeouts.
  - TimeoutError is treated the same as a provider failure — triggers fallback.
  - If ALL providers fail, raises VoiceProviderException with all error details.
"""

import asyncio
import logging
import time
from typing import Optional

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.models import TranscriptionResult, SynthesisResult
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.clients.voice.factories.stt_factory import STTFactory
from app.clients.voice.factories.tts_factory import TTSFactory
from app.clients.voice.session import VoiceSessionManager
from app.services.tts_audio_stitcher import TTSAudioStitcher
from app.services.tts_segment_router import TTSSegmentRouter

logger = logging.getLogger("ai_server.voice.gateway")

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

        # Build TTS providers lazily on first synthesis so interview text can
        # return immediately without waiting for heavyweight local TTS models.
        self.tts_providers: list[tuple[str, BaseTTSEngine]] = []
        self._tts_providers_lock: Optional[asyncio.Lock] = None

        # Session manager (Redis-backed)
        self.session = VoiceSessionManager()
        self.tts_router = TTSSegmentRouter()
        self.tts_stitcher = TTSAudioStitcher()

        logger.info(
            "VoiceGateway initialized: STT=%s, TTS=%s",
            [p[0] for p in self.stt_providers],
            "lazy",
        )

    async def _ensure_tts_providers(self) -> None:
        if self.tts_providers:
            return
        if self._tts_providers_lock is None:
            self._tts_providers_lock = asyncio.Lock()
        async with self._tts_providers_lock:
            if self.tts_providers:
                return
            try:
                self.tts_providers = await asyncio.to_thread(TTSFactory.all_providers)
            except Exception as exc:
                logger.error("Failed to build TTS providers: %s", exc)

            if not self.tts_providers:
                logger.critical("No TTS providers could be initialized")
                raise VoiceProviderException("No TTS providers available")

            logger.info("TTS providers initialized: %s", [p[0] for p in self.tts_providers])

    # ── Primary public methods ─────────────────────────────────

    async def transcribe_with_fallback(
        self,
        audio: bytes,
        language: str,
        hotwords: Optional[list[str]] = None,
        primary_language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio using the first available STT provider.

        Tries each provider in priority order. On failure, logs the error
        and tries the next provider. If all fail, raises VoiceProviderException.

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
            language: BCP-47 language hint ('vi', 'en') or 'auto'/'mixed'.
            hotwords: Optional job-specific words to bias STT providers.
            primary_language: Session primary language used when language is auto/mixed.

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
                    provider.transcribe(audio, language, hotwords, primary_language),
                    timeout=settings.STT_PROVIDER_TIMEOUT,
                )
                result.stt_provider = name
                result.fallback_used = name != primary_name
                if result.fallback_used:
                    logger.info("STT fallback used: %s (primary=%s)", name, primary_name)
                return result
            except asyncio.TimeoutError:
                message = f"timed out after {settings.STT_PROVIDER_TIMEOUT:.0f}s"
                logger.warning("STT provider '%s' failed: %s", name, message)
                errors.append(f"{name}: {message}")
                continue
            except Exception as exc:
                logger.exception("STT provider '%s' failed unexpectedly", name)
                errors.append(f"{name}: {exc}")
                continue

        raise VoiceProviderException(
            "All STT providers failed",
            errors=errors,
        )

    async def synthesize_with_fallback(
        self,
        text: str,
        language: str,
        hotwords: Optional[list[str]] = None,
    ) -> SynthesisResult:
        """Synthesize speech using the first available TTS provider.

        Args:
            text: Text to vocalize.
            language: BCP-47 language code ('vi' or 'en') for voice selection.

        Returns:
            SynthesisResult with provider metadata set.

        Raises:
            VoiceProviderException: If ALL providers fail.
        """
        await self._ensure_tts_providers()
        segments = self.tts_router.route(text, language, hotwords=hotwords)
        if len(segments) > 1:
            logger.info(
                "TTS segmented into %d voice routes: %s",
                len(segments),
                [segment.language for segment in segments],
            )

        results = [
            await self._synthesize_segment_with_fallback(segment.text, segment.language)
            for segment in segments
        ]
        if not results:
            raise VoiceProviderException("TTS text was empty")
        if len(results) == 1:
            return results[0]

        return self.tts_stitcher.stitch(results)

    async def _synthesize_segment_with_fallback(
        self, text: str, language: str
    ) -> SynthesisResult:
        errors: list[str] = []
        primary_name = self.tts_providers[0][0]

        for name, provider in self.tts_providers:
            try:
                started_at = time.perf_counter()
                logger.info(
                    "TTS provider '%s' started: chars=%d language=%s timeout=%.0fs",
                    name,
                    len(text),
                    language,
                    settings.TTS_PROVIDER_TIMEOUT,
                )
                result = await asyncio.wait_for(
                    provider.synthesize(text, language),
                    timeout=settings.TTS_PROVIDER_TIMEOUT,
                )
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                result.tts_provider = name
                result.fallback_used = name != primary_name
                logger.info(
                    "TTS provider '%s' completed: elapsed=%.0fms bytes=%d mime=%s",
                    name,
                    elapsed_ms,
                    len(result.audio_bytes),
                    result.mime_type,
                )
                if result.fallback_used:
                    logger.info("TTS fallback used: %s (primary=%s)", name, primary_name)
                return result
            except asyncio.TimeoutError:
                message = f"timed out after {settings.TTS_PROVIDER_TIMEOUT:.0f}s"
                logger.warning("TTS provider '%s' failed: %s", name, message)
                errors.append(f"{name}: {message}")
                continue
            except Exception as exc:
                logger.exception("TTS provider '%s' failed unexpectedly", name)
                errors.append(f"{name}: {exc}")
                continue

        raise VoiceProviderException(
            "All TTS providers failed",
            errors=errors,
        )
