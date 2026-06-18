"""Faster-Whisper STT engine — local-dev fallback (NOT for Render 512MB).

Loads the model LAZILY on the first transcribe() call — importing this module
does NOT allocate 150MB+ of RAM. This class is only instantiated when
STT_PRIMARY_PROVIDER or STT_FALLBACK_PROVIDER is set to "faster_whisper".

Receives pre-decoded WAV 16kHz mono PCM bytes from AudioProcessor.
Writes to a tempfile internally since CTranslate2 needs a file path for its decoder.
No system ffmpeg required because input is already WAV.
"""

import asyncio
import logging
import os
import tempfile
import numpy as np

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.clients.voice.models import TranscriptionResult

logger = logging.getLogger("ai_server.voice.faster_whisper")


class FasterWhisperEngine(BaseSTTEngine):
    """Faster-Whisper STT engine using CTranslate2 (CPU/int8).

    Model is loaded lazily on first transcribe() call.
    Intended for local development only — NOT suitable for Render 512MB free tier.
    """

    def __init__(self):
        self._model = None

    async def _get_model(self):
        """Lazy-load the WhisperModel on first use.

        This ensures importing this module or creating the engine object
        does NOT allocate 150MB+ of RAM. Memory is only consumed when
        transcribe() is actually called.
        """
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel

            model_size = settings.FASTER_WHISPER_MODEL
            logger.info(
                f"Loading Faster-Whisper model '{model_size}' "
                f"(device={settings.FASTER_WHISPER_DEVICE}, "
                f"compute={settings.FASTER_WHISPER_COMPUTE_TYPE})"
            )
            self._model = WhisperModel(
                model_size,
                device=settings.FASTER_WHISPER_DEVICE,
                compute_type=settings.FASTER_WHISPER_COMPUTE_TYPE,
            )
            logger.info("Faster-Whisper model loaded successfully")
            return self._model
        except ImportError:
            raise VoiceProviderException(
                "faster-whisper package not installed. "
                "Run: pip install faster-whisper"
            )
        except Exception as exc:
            raise VoiceProviderException(
                f"Failed to load Faster-Whisper model '{model_size}': {exc}"
            )

    async def transcribe(self, audio: bytes, language: str) -> TranscriptionResult:
        """Transcribe WAV PCM audio via Faster-Whisper.

        Args:
            audio: WAV 16-bit 16kHz mono PCM bytes (pre-decoded by AudioProcessor).
            language: BCP-47 hint ('vi' or 'en').

        Returns:
            TranscriptionResult with confidence from avg_logprob.

        Raises:
            VoiceProviderException: On model load failure, decode error, or timeout.
        """
        model = await self._get_model()

        # CTranslate2 needs a file path for audio decoding. Since audio is
        # already WAV PCM, write to a temp file.
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name

            lang_hint = language[:2] if language else "vi"

            # Run in a thread to avoid blocking the event loop
            # (WhisperModel.transcribe is CPU-bound)
            def _run():
                segments, info = model.transcribe(
                    tmp_path,
                    language=lang_hint,
                    beam_size=5,
                    vad_filter=True,
                )
                segments_list = list(segments)
                return segments_list, info

            segments_list, info = await asyncio.to_thread(_run)

            if not segments_list:
                raise VoiceProviderException(
                    "Faster-Whisper returned no segments — audio may be silent"
                )

            # Build full transcript and compute confidence from avg_logprob
            transcript_parts = []
            log_probs = []
            for seg in segments_list:
                transcript_parts.append(seg.text)
                if seg.avg_logprob is not None:
                    log_probs.append(seg.avg_logprob)

            full_text = " ".join(transcript_parts).strip()
            # Map avg_logprob (roughly -1.0 to 0.0) to 0-1 confidence
            avg_logprob = np.mean(log_probs) if log_probs else -1.0
            confidence = float(max(0.0, min(1.0, (avg_logprob + 1.0) / 1.0)))

            detected_lang = getattr(info, "language", lang_hint) or lang_hint

            return TranscriptionResult(
                text=full_text,
                language=detected_lang,
                confidence=confidence,
                stt_provider="faster_whisper",
            )

        except VoiceProviderException:
            raise
        except Exception as exc:
            raise VoiceProviderException(
                f"Faster-Whisper transcription failed: {exc}"
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
