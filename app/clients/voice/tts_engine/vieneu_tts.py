"""VieNeu TTS engine for local Vietnamese/English testing.

This provider wraps the optional `vieneu` SDK. It is intended as a local
development/testing provider; production can keep ElevenLabs as the primary
provider once that engine is wired.
"""

import asyncio
import io
import logging
import os
import time
import wave
from typing import Any

import numpy as np

from app.clients.voice.models import SynthesisResult
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.core.config import settings
from app.core.exceptions import VoiceProviderException

logger = logging.getLogger("ai_server.voice.vieneu_tts")


class VieNeuTTSEngine(BaseTTSEngine):
    """TTS engine backed by the optional VieNeu SDK."""

    def __init__(self):
        self._configure_huggingface_token()
        try:
            from vieneu import Vieneu
        except ImportError as exc:
            raise VoiceProviderException(
                "VieNeu TTS SDK is not installed. Run: pip install vieneu"
            ) from exc

        try:
            started_at = time.perf_counter()
            logger.info("Initializing VieNeu TTS engine")
            self._client = Vieneu()
            self._voice = self._load_voice()
            self._sample_rate = int(
                getattr(self._client, "sample_rate", None)
                or settings.VIENEU_SAMPLE_RATE
            )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "VieNeu TTS engine initialized: elapsed=%.0fms sample_rate=%d",
                elapsed_ms,
                self._sample_rate,
            )
        except Exception as exc:
            raise VoiceProviderException(f"VieNeu TTS failed to initialize: {exc}") from exc

    async def synthesize(self, text: str, language: str) -> SynthesisResult:
        """Synthesize speech and return WAV bytes."""
        if not text.strip():
            raise VoiceProviderException("VieNeu TTS text was empty")

        try:
            started_at = time.perf_counter()
            logger.info("VieNeu TTS synthesis started: chars=%d", len(text))
            audio = await asyncio.to_thread(self._infer_sync, text)
            audio_bytes = self._to_wav_bytes(audio, self._sample_rate)
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "VieNeu TTS synthesis completed: elapsed=%.0fms bytes=%d",
                elapsed_ms,
                len(audio_bytes),
            )
        except VoiceProviderException:
            raise
        except Exception as exc:
            raise VoiceProviderException(f"VieNeu TTS failed: {exc}") from exc

        if not audio_bytes:
            raise VoiceProviderException("VieNeu TTS returned empty audio")

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            tts_provider="vieneu",
        )

    def _load_voice(self):
        voice_id = (settings.VIENEU_VOICE_ID or "").strip()
        if not voice_id:
            return None
        if not hasattr(self._client, "get_preset_voice"):
            raise VoiceProviderException("VieNeu SDK does not support preset voices")
        return self._client.get_preset_voice(voice_id)

    @staticmethod
    def _configure_huggingface_token() -> None:
        token = (settings.HF_TOKEN or "").strip()
        if token and not os.environ.get("HF_TOKEN"):
            os.environ["HF_TOKEN"] = token

    def _infer_sync(self, text: str):
        if self._voice is not None:
            return self._client.infer(text=text, voice=self._voice)
        return self._client.infer(text=text)

    @classmethod
    def _to_wav_bytes(cls, audio: Any, default_sample_rate: int) -> bytes:
        """Normalize common SDK return shapes to mono 16-bit PCM WAV bytes."""
        sample_rate = default_sample_rate

        if isinstance(audio, (bytes, bytearray)):
            data = bytes(audio)
            if data.startswith(b"RIFF"):
                return data
            raise VoiceProviderException("VieNeu TTS returned raw bytes, not WAV bytes")

        if isinstance(audio, dict):
            sample_rate = int(
                audio.get("sample_rate")
                or audio.get("sampling_rate")
                or default_sample_rate
            )
            for key in ("audio", "waveform", "samples", "array"):
                if key in audio and audio[key] is not None:
                    audio = audio[key]
                    break

        if isinstance(audio, tuple) and len(audio) == 2:
            first, second = audio
            if isinstance(first, int):
                sample_rate = first
                audio = second
            elif isinstance(second, int):
                sample_rate = second
                audio = first

        if hasattr(audio, "audio"):
            sample_rate = int(
                getattr(audio, "sample_rate", None)
                or getattr(audio, "sampling_rate", None)
                or sample_rate
            )
            audio = getattr(audio, "audio")

        samples = np.asarray(audio)
        if samples.size == 0:
            raise VoiceProviderException("VieNeu TTS returned empty audio")

        samples = samples.squeeze()
        if samples.ndim == 2:
            axis = 0 if samples.shape[0] <= samples.shape[1] else 1
            samples = np.mean(samples, axis=axis)
        if samples.ndim != 1:
            raise VoiceProviderException("VieNeu TTS returned unsupported audio shape")

        if np.issubdtype(samples.dtype, np.floating):
            samples = np.clip(samples, -1.0, 1.0)
            samples = (samples * 32767).astype(np.int16)
        else:
            samples = np.clip(samples, -32768, 32767).astype(np.int16)

        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(samples.tobytes())
        return output.getvalue()
