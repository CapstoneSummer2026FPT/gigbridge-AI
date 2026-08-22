"""
PURPOSE: Audio validation, universal PyAV decoding to 16kHz mono PCM, and RMS silence detection.
IMPORTANCE: Critical — Core audio processing pipeline converting all incoming formats into normalized LINEAR16 PCM.
READING FLOW: app/services/audio/audio_processor.py -> app/services/audio/voice.py
"""

import io
import logging
import struct
import wave
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.exceptions import AudioValidationError

logger = logging.getLogger("ai_server.audio_processor")


class AudioProcessor:
    """Validates, decodes, and analyzes audio input into WAV 16-bit 16kHz mono PCM via PyAV."""

    _TYPE_ALIASES = {
        "audio/x-wav": "audio/wav",
        "audio/x-mpeg": "audio/mpeg",
        "audio/x-mp4": "audio/mp4",
    }

    def __init__(self):
        """Initialize AudioProcessor with configuration parameters."""
        self.accepted_types = list(settings.ACCEPTED_AUDIO_TYPES)
        self.max_size = settings.AUDIO_MAX_SIZE_BYTES
        self.max_duration = settings.AUDIO_MAX_DURATION_SECONDS
        self.silence_threshold = settings.AUDIO_SILENCE_THRESHOLD
        self.target_sample_rate = settings.AUDIO_DECODE_SAMPLE_RATE

    def validate_request(self, content_type: Optional[str], content_length_header: str) -> int:
        """Validate Content-Type and Content-Length from request headers before reading request body.
        
        Flow:
        1. Normalize content-type header.
        2. Check against accepted content types.
        3. Parse content length header and enforce maximum upload size.
        """
        normalized_type = self._normalize_content_type(content_type or "")
        if normalized_type not in self.accepted_types:
            logger.warning("Rejected unsupported audio type: %s", content_type)
            raise AudioValidationError("unsupported_audio_type", 415)

        if content_length_header:
            try:
                size = int(content_length_header)
                if size > self.max_size:
                    logger.warning("Rejected oversized upload: %d bytes (max %d)", size, self.max_size)
                    raise AudioValidationError("upload_too_large", 413)
                return size
            except (ValueError, TypeError):
                pass

        return 0

    def validate_bytes(self, audio_bytes: bytes) -> None:
        """Hard backstop — validate byte length after reading request body."""
        if len(audio_bytes) > self.max_size:
            logger.warning("Byte backstop triggered: %d bytes (max %d)", len(audio_bytes), self.max_size)
            raise AudioValidationError("upload_too_large", 413)

    def decode_and_normalize(self, audio_bytes: bytes) -> bytes:
        """Decode ANY input format (webm/opus, mp3, wav, mp4) to WAV 16-bit 16kHz mono PCM via PyAV.
        
        Flow:
        1. Open PyAV input container on BytesIO buffer.
        2. Create AudioResampler configured for s16 format, mono layout, 16kHz sample rate.
        3. Decode audio frames and aggregate int16 PCM arrays.
        4. Validate decoded PCM audio duration against maximum duration.
        5. Build and return complete WAV bytes with standard RIFF header.
        """
        try:
            import av as _av
        except ImportError:
            raise AudioValidationError(
                "audio_decode_failed", 500,
                errors=["PyAV (av) package not installed"],
            )

        try:
            input_container = _av.open(io.BytesIO(audio_bytes))
        except Exception as exc:
            raise AudioValidationError(
                "audio_decode_failed", 400,
                errors=[f"Cannot open audio container: {exc}"],
            )

        pcm_chunks: list[np.ndarray] = []
        try:
            resampler = _av.AudioResampler(
                format="s16",
                layout="mono",
                rate=self.target_sample_rate,
            )
            for frame in input_container.decode(audio=0):
                for normalized_frame in resampler.resample(frame):
                    pcm_chunks.append(
                        normalized_frame.to_ndarray().reshape(-1).astype(np.int16)
                    )
            for normalized_frame in resampler.resample(None):
                pcm_chunks.append(
                    normalized_frame.to_ndarray().reshape(-1).astype(np.int16)
                )
        except Exception as exc:
            raise AudioValidationError(
                "audio_decode_failed", 400,
                errors=[f"Audio decode error: {exc}"],
            )
        finally:
            input_container.close()

        if not pcm_chunks:
            raise AudioValidationError("no_speech_detected", 400)

        pcm_int16 = np.concatenate(pcm_chunks)

        duration_seconds = len(pcm_int16) / self.target_sample_rate
        if duration_seconds > self.max_duration:
            raise AudioValidationError(
                "audio_too_long", 400,
                errors=[f"Duration {duration_seconds:.1f}s exceeds max {self.max_duration}s"],
            )

        return self._build_wav(pcm_int16)

    def detect_silence(self, pcm_wav_bytes: bytes) -> bool:
        """Detect if decoded PCM audio is silent using numpy RMS calculation."""
        if len(pcm_wav_bytes) < 44:
            return True

        try:
            import numpy as _np
            samples = _np.frombuffer(pcm_wav_bytes[44:], dtype=_np.int16).astype(_np.float32)
            if len(samples) == 0:
                return True

            rms = float(_np.sqrt(_np.mean(samples ** 2)))
            threshold_scaled = self.silence_threshold * 32768
            is_silent = rms < threshold_scaled

            if is_silent:
                logger.debug("Silence detected: RMS=%.2f (threshold=%.2f)", rms, threshold_scaled)
            return is_silent
        except Exception as exc:
            logger.warning("Silence detection failed: %s — accepting audio", exc)
            return False

    @staticmethod
    def _resample_numpy(arr: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """Resample mono audio array using numpy linear interpolation."""
        if arr.shape[0] != 1:
            raise ValueError("Expected mono audio (shape=[1, n])")
        src_len = arr.shape[1]
        dst_len = int(src_len * dst_rate / src_rate)
        if dst_len < 1:
            return np.zeros((1, 1), dtype=np.float32)
        x_old = np.linspace(0, src_len - 1, src_len)
        x_new = np.linspace(0, src_len - 1, dst_len)
        resampled = np.interp(x_new, x_old, arr[0]).reshape(1, -1)
        return resampled.astype(np.float32)

    def _build_wav(self, pcm_int16: np.ndarray) -> bytes:
        """Build complete WAV file from int16 PCM array using stdlib wave module."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.target_sample_rate)
            wf.writeframes(pcm_int16.tobytes())
        return buf.getvalue()

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        """Normalize Content-Type header."""
        import cgi
        main_type = cgi.parse_header(content_type)[0].strip().lower()
        return AudioProcessor._TYPE_ALIASES.get(main_type, main_type)
