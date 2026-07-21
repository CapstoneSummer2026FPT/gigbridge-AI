"""Audio Processor — universal decode + silence detection.

Central design principle: Every audio format (webm/opus, mp3, wav, mp4)
is decoded to WAV 16kHz mono PCM via PyAV before any STT engine sees it.

This single decode step fixes THREE architectural issues at once:
 1. Faster-Whisper receives WAV → CTranslate2 works without system ffmpeg
 2. Google STT receives LINEAR16 → no WEBM_OPUS header-chunking issues
 3. Silence detection runs on decoded PCM → RMS is mathematically meaningful

Upload guard chain:
  1. Content-Type check (from request.headers, before reading body)
  2. Content-Length check (from request.headers, before reading body)
  3. Byte-length backstop (after reading body — hard limit)
  4. Duration check (after decode — PCM sample count / sample rate)
  5. Silence detection (on decoded PCM — not on compressed bytes)
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
    """Validates, decodes, and analyzes audio input.

    All audio formats are decoded to WAV 16-bit 16kHz mono PCM via PyAV.
    Silence detection uses numpy RMS on the decoded PCM.
    """

    # Content-Type normalization maps
    _TYPE_ALIASES = {
        "audio/x-wav": "audio/wav",
        "audio/x-mpeg": "audio/mpeg",
        "audio/x-mp4": "audio/mp4",
    }

    def __init__(self):
        self.accepted_types = list(settings.ACCEPTED_AUDIO_TYPES)
        self.max_size = settings.AUDIO_MAX_SIZE_BYTES
        self.max_duration = settings.AUDIO_MAX_DURATION_SECONDS
        self.silence_threshold = settings.AUDIO_SILENCE_THRESHOLD
        self.target_sample_rate = settings.AUDIO_DECODE_SAMPLE_RATE

    # ── Upload Guards ──────────────────────────────────────────

    def validate_request(self, content_type: Optional[str], content_length_header: str) -> int:
        """Validate Content-Type and Content-Length from request HEADERS.

        Called BEFORE reading the body — fast rejection of invalid uploads.
        Returns the expected size in bytes (0 if unknown).

        Raises:
            AudioValidationError: On invalid type or oversized upload.
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
                pass  # invalid header — will check after read

        return 0  # unknown size

    def validate_bytes(self, audio_bytes: bytes) -> None:
        """Hard backstop — validate byte length after reading the body.

        Raises:
            AudioValidationError: If bytes exceed the maximum.
        """
        if len(audio_bytes) > self.max_size:
            logger.warning("Byte backstop triggered: %d bytes (max %d)", len(audio_bytes), self.max_size)
            raise AudioValidationError("upload_too_large", 413)

    # ── Universal Decode ───────────────────────────────────────

    def decode_and_normalize(self, audio_bytes: bytes) -> bytes:
        """Decode ANY input format to WAV 16-bit 16kHz mono PCM via PyAV.

        Args:
            audio_bytes: Raw bytes in any supported format (webm/opus, mp3, wav, mp4).

        Returns:
            Complete WAV file bytes (RIFF header + PCM data).

        Raises:
            AudioValidationError: On decode failure or empty audio.
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

        audio_frames = []
        try:
            for frame in input_container.decode(audio=0):
                # Convert frame to float32 numpy array
                arr = frame.to_ndarray()

                # Stereo → mono: average channels
                if arr.shape[0] > 1:
                    arr = np.mean(arr, axis=0, keepdims=True)

                # Resample to target sample rate
                if frame.sample_rate != self.target_sample_rate:
                    arr = self._resample_numpy(arr, frame.sample_rate, self.target_sample_rate)

                audio_frames.append(arr.astype(np.float32))
        except Exception as exc:
            raise AudioValidationError(
                "audio_decode_failed", 400,
                errors=[f"Audio decode error: {exc}"],
            )
        finally:
            input_container.close()

        if not audio_frames:
            raise AudioValidationError("no_speech_detected", 400)

        # Concatenate all frames
        full = np.concatenate(audio_frames, axis=1)

        # Normalize to int16 range if signal is above background noise floor
        peak = np.max(np.abs(full))
        if peak > 0.01:
            full = full / peak * 0.95  # headroom
        pcm_int16 = (full[0] * 32767).astype(np.int16)

        # Check duration
        duration_seconds = len(pcm_int16) / self.target_sample_rate
        if duration_seconds > self.max_duration:
            raise AudioValidationError(
                "audio_too_long", 400,
                errors=[f"Duration {duration_seconds:.1f}s exceeds max {self.max_duration}s"],
            )

        # Build WAV using stdlib wave module
        return self._build_wav(pcm_int16)

    # ── Silence Detection ──────────────────────────────────────

    def detect_silence(self, pcm_wav_bytes: bytes) -> bool:
        """Detect if decoded PCM audio is silent.

        Only meaningful on LINEAR PCM — compressed audio RMS is garbage.
        Must be called AFTER decode_and_normalize().

        Returns:
            True if the audio is below the silence threshold.
        """
        if len(pcm_wav_bytes) < 44:  # minimum WAV header
            return True

        try:
            import numpy as _np
            # Skip WAV header, interpret as int16 PCM
            samples = _np.frombuffer(pcm_wav_bytes[44:], dtype=_np.int16).astype(_np.float32)
            if len(samples) == 0:
                return True

            rms = float(_np.sqrt(_np.mean(samples ** 2)))
            # Scale threshold to int16 range
            threshold_scaled = self.silence_threshold * 32768
            is_silent = rms < threshold_scaled

            if is_silent:
                logger.debug("Silence detected: RMS=%.2f (threshold=%.2f)", rms, threshold_scaled)
            return is_silent
        except Exception as exc:
            logger.warning("Silence detection failed: %s — accepting audio", exc)
            return False  # accept on detection failure

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    def _resample_numpy(arr: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """Resample audio from src_rate to dst_rate using numpy interpolation.

        For speech content resampled to 16kHz, linear interpolation is adequate
        (speech fundamental frequencies are 85-255Hz, well below the 8kHz Nyquist
        limit at 16kHz). The aliasing concern from higher frequencies is negligible
        for STT applications.
        """
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
        """Build a complete WAV file from int16 PCM data using stdlib wave.

        Safer and more reliable than manual RIFF header construction.
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.target_sample_rate)
            wf.writeframes(pcm_int16.tobytes())
        return buf.getvalue()

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        """Normalize Content-Type: strip parameters, normalize whitespace, apply aliases.

        Browsers may send 'audio/webm; codecs=opus' or 'audio/webm;codecs=opus'.
        This normalizes the base type before comparison.
        """
        import cgi
        main_type = cgi.parse_header(content_type)[0].strip().lower()
        return AudioProcessor._TYPE_ALIASES.get(main_type, main_type)
