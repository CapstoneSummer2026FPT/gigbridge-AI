"""
PURPOSE: WAV audio window chunking for long local STT transcription.
IMPORTANCE: High — Splits long audio files into overlapping windows to prevent memory exhaustion during STT transcription.
READING FLOW: app/services/audio/audio_chunker.py -> app/clients/voice/providers/stt_faster_whisper.py
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import wave

from app.core.config import settings


@dataclass(frozen=True)
class AudioChunk:
    """Dataclass holding chunk metadata and raw WAV bytes."""
    index: int
    start_seconds: float
    end_seconds: float
    wav_bytes: bytes


class AudioChunker:
    """Splits decoded WAV audio into overlapping windows."""

    def __init__(
        self,
        chunk_seconds: int | None = None,
        overlap_seconds: int | None = None,
    ):
        """Initialize AudioChunker with window and overlap durations."""
        self.chunk_seconds = (
            settings.FASTER_WHISPER_CHUNK_SECONDS
            if chunk_seconds is None
            else chunk_seconds
        )
        self.overlap_seconds = (
            settings.FASTER_WHISPER_CHUNK_OVERLAP_SECONDS
            if overlap_seconds is None
            else overlap_seconds
        )
        if self.chunk_seconds <= 0:
            raise ValueError("chunk_seconds must be positive")
        if self.overlap_seconds < 0:
            raise ValueError("overlap_seconds cannot be negative")
        if self.overlap_seconds >= self.chunk_seconds:
            raise ValueError("overlap_seconds must be smaller than chunk_seconds")

    def split_wav(self, wav_bytes: bytes) -> list[AudioChunk]:
        """Split decoded WAV audio bytes into a list of AudioChunk windows.
        
        Flow:
        1. Read WAV header parameters and raw PCM frames.
        2. Check if total audio duration is smaller than chunk size; return single chunk if so.
        3. Step through audio frames in overlapping window strides.
        4. Rebuild WAV header for each slice and return AudioChunk list.
        """
        params, frames = self._read_wav(wav_bytes)
        sample_rate = params.framerate
        total_frames = params.nframes
        chunk_frames = int(self.chunk_seconds * sample_rate)
        overlap_frames = int(self.overlap_seconds * sample_rate)

        if total_frames <= chunk_frames:
            return [
                AudioChunk(
                    index=0,
                    start_seconds=0.0,
                    end_seconds=total_frames / sample_rate,
                    wav_bytes=wav_bytes,
                )
            ]

        chunks: list[AudioChunk] = []
        frame_width = params.nchannels * params.sampwidth
        step_frames = chunk_frames - overlap_frames
        start = 0
        index = 0

        while start < total_frames:
            end = min(start + chunk_frames, total_frames)
            frame_slice = frames[start * frame_width : end * frame_width]
            chunks.append(
                AudioChunk(
                    index=index,
                    start_seconds=start / sample_rate,
                    end_seconds=end / sample_rate,
                    wav_bytes=self._build_wav(params, frame_slice),
                )
            )
            if end >= total_frames:
                break
            start += step_frames
            index += 1

        return chunks

    @staticmethod
    def _read_wav(wav_bytes: bytes) -> tuple[wave._wave_params, bytes]:
        """Read header parameters and frames from WAV bytes."""
        with wave.open(io.BytesIO(wav_bytes), "rb") as reader:
            params = reader.getparams()
            frames = reader.readframes(params.nframes)
        return params, frames

    @staticmethod
    def _build_wav(params: wave._wave_params, frame_bytes: bytes) -> bytes:
        """Rebuild WAV container from header parameters and frame slice."""
        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(params.nchannels)
            writer.setsampwidth(params.sampwidth)
            writer.setframerate(params.framerate)
            writer.writeframes(frame_bytes)
        return output.getvalue()
