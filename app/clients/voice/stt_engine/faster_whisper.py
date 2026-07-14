"""Faster-Whisper STT engine with optional long-audio chunking."""

import asyncio
import logging
import os
import tempfile
import time
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.clients.voice.models import TranscriptionResult
from app.services.audio_chunker import AudioChunker

logger = logging.getLogger("ai_server.voice.faster_whisper")


class FasterWhisperEngine(BaseSTTEngine):
    """Faster-Whisper STT engine using CTranslate2 (CPU/int8)."""

    def __init__(self):
        self._model = None
        self._model_load_task: Optional[asyncio.Task] = None
        self._chunker = AudioChunker()

    async def _load_model(self):
        """Construct the blocking model off the event loop."""
        model_size = settings.FASTER_WHISPER_MODEL
        try:
            from faster_whisper import WhisperModel

            logger.info(
                f"Loading Faster-Whisper model '{model_size}' "
                f"(device={settings.FASTER_WHISPER_DEVICE}, "
                f"compute={settings.FASTER_WHISPER_COMPUTE_TYPE})"
            )
            self._model = await asyncio.to_thread(
                WhisperModel,
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

    async def _get_model(self):
        """Lazy-load one shared model without blocking or duplicating work."""
        if self._model is not None:
            return self._model
        if self._model_load_task is None:
            self._model_load_task = asyncio.create_task(self._load_model())
        try:
            return await asyncio.shield(self._model_load_task)
        except Exception:
            if self._model_load_task.done():
                self._model_load_task = None
            raise

    async def transcribe(
        self,
        audio: bytes,
        language: str,
        hotwords: Optional[list[str]] = None,
        primary_language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe decoded WAV audio via Faster-Whisper."""
        model = await self._get_model()

        try:
            requested = (language or "").strip().lower()
            primary_hint = (primary_language or "").strip().lower()
            lang_hint = (
                None
                if requested in {"auto", "mixed"}
                else (requested or primary_hint or "vi")[:2]
            )
            initial_prompt = self._build_initial_prompt(hotwords)
            logger.info(
                "Faster-Whisper transcribe: requested=%s primary=%s lang_hint=%s audio_bytes=%d",
                requested or "none",
                primary_hint or "none",
                lang_hint,
                len(audio),
            )

            chunks = self._chunker.split_wav(audio)
            if len(chunks) > 1:
                logger.info("Faster-Whisper chunking audio into %d windows", len(chunks))

            transcript_parts: list[str] = []
            log_probs: list[float] = []
            detected_lang = lang_hint or "auto"

            for chunk in chunks:
                text, chunk_log_probs, chunk_lang = await self._transcribe_wav_bytes(
                    model=model,
                    wav_bytes=chunk.wav_bytes,
                    language=lang_hint,
                    initial_prompt=initial_prompt,
                )
                if text:
                    transcript_parts = self._append_with_overlap_dedup(
                        transcript_parts, text
                    )
                log_probs.extend(chunk_log_probs)
                if chunk_lang and detected_lang == "auto":
                    detected_lang = chunk_lang

            if not transcript_parts:
                raise VoiceProviderException(
                    "Faster-Whisper returned no segments - audio may be silent"
                )

            full_text = " ".join(transcript_parts).strip()
            avg_logprob = np.mean(log_probs) if log_probs else -1.0
            confidence = float(max(0.0, min(1.0, avg_logprob + 1.0)))
            logger.info(
                "Faster-Whisper result: detected_language=%s confidence=%.2f chars=%d",
                detected_lang,
                confidence,
                len(full_text),
            )

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

    @staticmethod
    def _build_initial_prompt(hotwords: Optional[list[str]]) -> Optional[str]:
        cleaned_hotwords = [
            word.strip() for word in (hotwords or []) if word and word.strip()
        ]
        if not cleaned_hotwords:
            return None
        return "[Context: " + ", ".join(cleaned_hotwords) + "]"

    @staticmethod
    async def _transcribe_wav_bytes(
        model,
        wav_bytes: bytes,
        language: Optional[str],
        initial_prompt: Optional[str],
    ) -> tuple[str, list[float], Optional[str]]:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            def _run():
                segments, info = model.transcribe(
                    tmp_path,
                    language=language,
                    initial_prompt=initial_prompt,
                    beam_size=5,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                return list(segments), info

            segments_list, info = await asyncio.to_thread(_run)
            transcript_parts: list[str] = []
            log_probs: list[float] = []
            for seg in segments_list:
                transcript_parts.append(seg.text)
                if seg.avg_logprob is not None:
                    log_probs.append(seg.avg_logprob)

            text = " ".join(transcript_parts).strip()
            detected_language = getattr(info, "language", language) or language
            return text, log_probs, detected_language
        finally:
            if tmp_path and os.path.exists(tmp_path):
                for attempt in range(3):
                    try:
                        os.unlink(tmp_path)
                        break
                    except PermissionError as exc:
                        if attempt == 2:
                            logger.warning(
                                "Could not delete temporary STT wav file yet: %s",
                                exc,
                            )
                            break
                        time.sleep(0.1)

    @staticmethod
    def _append_with_overlap_dedup(parts: list[str], next_text: str) -> list[str]:
        if not parts:
            return [next_text]

        previous_words = parts[-1].split()
        next_words = next_text.split()
        max_overlap = min(12, len(previous_words), len(next_words))
        overlap = 0

        for size in range(max_overlap, 0, -1):
            left = " ".join(previous_words[-size:]).casefold()
            right = " ".join(next_words[:size]).casefold()
            if left == right:
                overlap = size
                break

        if overlap:
            deduped = " ".join(next_words[overlap:]).strip()
            if deduped:
                return [*parts, deduped]
            return parts
        return [*parts, next_text]
