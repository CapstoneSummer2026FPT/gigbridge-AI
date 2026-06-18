"""TTS Factory — builds the configured TTS engine from environment config.

Edge TTS is listed first (free, no API key).
Google TTS is listed second (requires credentials, higher quality).
"""

import logging

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.tts_engine.base import BaseTTSEngine

logger = logging.getLogger("ai_server.voice.tts_factory")


class TTSFactory:
    """Builds TTS engine instances from config."""

    @staticmethod
    def create(provider_name: str = None) -> BaseTTSEngine:
        """Create and return the configured TTS engine.

        Args:
            provider_name: Provider to create (default: settings.TTS_PRIMARY_PROVIDER).

        Returns:
            A BaseTTSEngine instance.

        Raises:
            VoiceProviderException: If the provider is unknown or its deps missing.
        """
        provider = provider_name or settings.TTS_PRIMARY_PROVIDER

        if provider == "edge_tts":
            from app.clients.voice.tts_engine.edge_tts_engine import EdgeTTSEngine

            return EdgeTTSEngine()

        elif provider == "google":
            from app.clients.voice.tts_engine.google_tts import GoogleTTSEngine

            return GoogleTTSEngine()

        else:
            raise VoiceProviderException(
                f"Unknown TTS provider: {provider}. "
                f"Supported: edge_tts, google"
            )

    @staticmethod
    def all_providers() -> list[tuple[str, BaseTTSEngine]]:
        """Build all available TTS providers. Skips ones that fail to init.

        Returns:
            List of (provider_name, engine) tuples, ordered by priority:
            edge_tts first, then google.
        """
        providers = []
        for name in ["edge_tts", "google"]:
            try:
                engine = TTSFactory.create(name)
                providers.append((name, engine))
            except Exception as exc:
                logger.warning(f"TTS provider '{name}' failed to init: {exc}")
                continue
        return providers
