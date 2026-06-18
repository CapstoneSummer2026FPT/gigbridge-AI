"""Abstract base class for all STT (Speech-to-Text) providers.

CONTRACT — every engine MUST follow this:
  - Raises VoiceProviderException on failure. Never returns a degraded result.
  - The gateway catches exceptions and chains to the fallback provider.
  - Returning a TranscriptionResult means "this succeeded authoritatively."
  - Input is always WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
    Engines do NOT handle format conversion.
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.clients.voice.models import TranscriptionResult


class BaseSTTEngine(ABC):
    """Abstract interface that every STT provider must implement."""

    @abstractmethod
    async def transcribe(self, audio: bytes, language: str) -> TranscriptionResult:
        """Transcribe WAV PCM audio to text.

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes. The AudioProcessor.decode_and_normalize()
                   step runs BEFORE this engine is called — all formats (webm/opus, mp3, mp4)
                   have been decoded to WAV PCM. Engines do NOT need ffmpeg or format handling.
            language: BCP-47 language hint ('vi' or 'en').

        Returns:
            TranscriptionResult on success.

        Raises:
            VoiceProviderException: On any failure (API error, decode error, timeout).
                                   The gateway catches this and tries the fallback.
                                   Do NOT return an empty or partial result on failure.
        """
        ...
