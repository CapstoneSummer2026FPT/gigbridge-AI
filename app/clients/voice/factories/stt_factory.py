"""STT Factory — builds the configured STT engine from environment config.

The factory reads STT_PRIMARY_PROVIDER / STT_FALLBACK_PROVIDER and returns
the appropriate engine instances. It does NOT handle fallback logic —
that is the gateway's responsibility.
"""

import logging

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.stt_engine.base import BaseSTTEngine

logger = logging.getLogger("ai_server.voice.stt_factory")


class STTFactory:
    """Builds STT engine instances from config.

    Usage:
        engine = STTFactory.create()  # Returns the configured engine
    """

    @staticmethod
    def create(provider_name: str = None) -> BaseSTTEngine:
        """Create and return the configured STT engine.

        Args:
            provider_name: Provider to create (default: settings.STT_PRIMARY_PROVIDER).

        Returns:
            A BaseSTTEngine instance.

        Raises:
            VoiceProviderException: If the provider is unknown or its dependencies
                                   are missing.
        """
        provider = provider_name or settings.STT_PRIMARY_PROVIDER

        if provider == "google":
            from app.clients.voice.stt_engine.google_stt import GoogleSTTEngine

            return GoogleSTTEngine()

        elif provider == "faster_whisper":
            from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

            return FasterWhisperEngine()

        else:
            raise VoiceProviderException(
                f"Unknown STT provider: {provider}. "
                f"Supported: google, faster_whisper"
            )

    @staticmethod
    def all_providers() -> list[tuple[str, BaseSTTEngine]]:
        """Build all available STT providers. Skips ones that fail to init.

        Returns:
            List of (provider_name, engine) tuples, ordered by priority:
            google first, then faster_whisper.
        """
        providers = []
        for name in ["google", "faster_whisper"]:
            try:
                engine = STTFactory.create(name)
                providers.append((name, engine))
            except Exception as exc:
                logger.warning(f"STT provider '{name}' failed to init: {exc}")
                continue
        return providers
