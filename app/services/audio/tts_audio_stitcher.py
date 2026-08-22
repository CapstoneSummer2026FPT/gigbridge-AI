"""
PURPOSE: Multi-voice TTS segment decoding, crossfading, peak normalization, and WAV audio stitching.
IMPORTANCE: High — Ensures smooth transitions and consistent audio volume across synthesized TTS segments.
READING FLOW: app/services/audio/tts_audio_stitcher.py -> app/services/interviews/interview_tts.py
"""

import io
import wave
import numpy as np

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.models import SynthesisResult


class TTSAudioStitcher:
    """Stitches synthesized TTS segments into one normalized WAV response."""

    def __init__(
        self,
        sample_rate: int | None = None,
        crossfade_ms: int | None = None,
        peak: float | None = None,
    ):
        """Initialize TTSAudioStitcher with target sample rate, crossfade, and peak normalization target."""
        self.sample_rate = sample_rate or settings.TTS_STITCH_SAMPLE_RATE
        self.crossfade_ms = crossfade_ms if crossfade_ms is not None else settings.TTS_STITCH_CROSSFADE_MS
        self.peak = peak if peak is not None else settings.TTS_STITCH_PEAK

    def stitch(self, segments: list[SynthesisResult]) -> SynthesisResult:
        """Stitch a list of SynthesisResult audio segments into a single WAV response.
        
        Flow:
        1. Decode each segment to floating point PCM sample arrays (via stdlib wave or PyAV).
        2. Apply short linear crossfade across adjacent segment boundaries.
        3. Normalize peak volume to specified peak target.
        4. Encode final float array to 16-bit WAV bytes and return SynthesisResult.
        """
        if not segments:
            raise VoiceProviderException("No TTS audio segments to stitch")
        if len(segments) == 1:
            return segments[0]

        pcm_segments = [
            self._decode_to_pcm(segment.audio_bytes, segment.mime_type)
            for segment in segments
        ]
        stitched = self._crossfade(pcm_segments)
        normalized = self._normalize_peak(stitched)
        audio_bytes = self._build_wav(normalized)

        providers = []
        for segment in segments:
            if segment.tts_provider not in providers:
                providers.append(segment.tts_provider)

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            tts_provider="+".join(providers),
            fallback_used=any(segment.fallback_used for segment in segments),
        )

    def _decode_to_pcm(self, audio_bytes: bytes, mime_type: str) -> np.ndarray:
        """Decode audio segment to float32 PCM array."""
        if not audio_bytes:
            raise VoiceProviderException("TTS provider returned empty segment audio")
        if self._looks_like_wav(audio_bytes, mime_type):
            return self._decode_wav(audio_bytes)
        return self._decode_with_av(audio_bytes)

    @staticmethod
    def _looks_like_wav(audio_bytes: bytes, mime_type: str) -> bool:
        """Check if audio bytes represent a WAV file."""
        return mime_type == "audio/wav" or audio_bytes.startswith(b"RIFF")

    def _decode_wav(self, audio_bytes: bytes) -> np.ndarray:
        """Decode WAV bytes using stdlib wave module."""
        with wave.open(io.BytesIO(audio_bytes), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frames = reader.readframes(reader.getnframes())

        if sample_width != 2:
            raise VoiceProviderException("Only 16-bit WAV TTS segments are supported")

        samples = np.frombuffer(frames, dtype=np.int16)
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)
        samples = samples.astype(np.float32) / 32768.0
        if sample_rate != self.sample_rate:
            samples = self._resample_linear(samples, sample_rate, self.sample_rate)
        return samples

    def _decode_with_av(self, audio_bytes: bytes) -> np.ndarray:
        """Decode compressed audio (MP3/AAC) using PyAV."""
        try:
            import av as _av
        except ImportError as exc:
            raise VoiceProviderException(
                "PyAV (av) is required to stitch compressed TTS segments"
            ) from exc

        try:
            container = _av.open(io.BytesIO(audio_bytes))
            resampler = _av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono",
                rate=self.sample_rate,
            )
            chunks = []
            for frame in container.decode(audio=0):
                for resampled in resampler.resample(frame):
                    array = resampled.to_ndarray()
                    chunks.append(array.reshape(-1).astype(np.float32) / 32768.0)
            for resampled in resampler.resample(None):
                array = resampled.to_ndarray()
                chunks.append(array.reshape(-1).astype(np.float32) / 32768.0)
        except Exception as exc:
            raise VoiceProviderException(f"Failed to decode TTS segment: {exc}") from exc

        if not chunks:
            raise VoiceProviderException("Decoded TTS segment was empty")
        return np.concatenate(chunks)

    def _crossfade(self, segments: list[np.ndarray]) -> np.ndarray:
        """Crossfade adjacent PCM sample arrays."""
        nonempty = [segment for segment in segments if len(segment)]
        if not nonempty:
            raise VoiceProviderException("All decoded TTS segments were empty")

        output = nonempty[0]
        fade_samples = max(0, int(self.sample_rate * self.crossfade_ms / 1000))
        for segment in nonempty[1:]:
            overlap = min(fade_samples, len(output), len(segment))
            if overlap <= 0:
                output = np.concatenate([output, segment])
                continue

            fade_out = np.linspace(1.0, 0.0, overlap, endpoint=False, dtype=np.float32)
            fade_in = np.linspace(0.0, 1.0, overlap, endpoint=False, dtype=np.float32)
            blended = output[-overlap:] * fade_out + segment[:overlap] * fade_in
            output = np.concatenate([output[:-overlap], blended, segment[overlap:]])
        return output

    def _normalize_peak(self, samples: np.ndarray) -> np.ndarray:
        """Normalize peak volume of PCM sample array."""
        peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
        if peak <= 0.0:
            return samples
        target = max(0.0, min(float(self.peak), 1.0))
        return np.clip(samples * (target / peak), -1.0, 1.0)

    @staticmethod
    def _resample_linear(
        samples: np.ndarray,
        source_rate: int,
        target_rate: int,
    ) -> np.ndarray:
        """Resample PCM array using linear interpolation."""
        if source_rate == target_rate or len(samples) == 0:
            return samples
        duration = len(samples) / source_rate
        target_length = max(1, int(round(duration * target_rate)))
        source_positions = np.linspace(0.0, duration, len(samples), endpoint=False)
        target_positions = np.linspace(0.0, duration, target_length, endpoint=False)
        return np.interp(target_positions, source_positions, samples).astype(np.float32)

    def _build_wav(self, samples: np.ndarray) -> bytes:
        """Build 16-bit WAV bytes from float32 PCM sample array."""
        pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(self.sample_rate)
            writer.writeframes(pcm.tobytes())
        return output.getvalue()
