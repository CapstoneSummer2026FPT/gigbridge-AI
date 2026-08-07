"""Abstract base class for all TTS (Text-to-Speech) providers.

CONTRACT — mirrors BaseSTTEngine:
  - Raises VoiceProviderException on failure. Never returns a degraded result.
  - The gateway catches exceptions and chains to the fallback provider.
  - Returning a SynthesisResult means "this succeeded authoritatively."
"""

from abc import ABC, abstractmethod

from app.clients.voice.models import SynthesisResult


class BaseTTSEngine(ABC):
    """Abstract interface that every TTS provider must implement."""

    @abstractmethod
    async def synthesize(self, text: str, language: str) -> SynthesisResult:
        """Synthesize text to speech audio.

        Args:
            text: Text to vocalize.
            language: BCP-47 language code ('vi' or 'en'). Used to select
                     the appropriate voice (e.g. vi-VN-HoaiMyNeural for Vietnamese).

        Returns:
            SynthesisResult on success.

        Raises:
            VoiceProviderException: On any failure (API error, timeout, network).
                                   The gateway catches this and tries the fallback.
                                   Do NOT return an empty or partial result on failure.
        """
        ...
