"""Gladia v2 Live Speech-to-Text engine using Solaria-3."""

import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from app.clients.voice.models import TranscriptionResult
from app.clients.voice.stt_engine.base import BaseSTTEngine
from app.core.config import settings
from app.core.exceptions import VoiceProviderException

logger = logging.getLogger("ai_server.voice.gladia_stt")

_AUDIO_CHUNK_BYTES = 64 * 1024


class GladiaSTTEngine(BaseSTTEngine):
    """Send normalized WAV audio through a configured Gladia Live session."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        if not settings.GLADIA_API_KEY.strip():
            raise VoiceProviderException("GLADIA_API_KEY not configured")
        self._client = client

    @staticmethod
    def build_session_config() -> dict[str, Any]:
        """Return the project's required Gladia Live configuration."""
        return {
            "encoding": "wav/pcm",
            "bit_depth": 16,
            "sample_rate": settings.AUDIO_DECODE_SAMPLE_RATE,
            "channels": 1,
            "model": "solaria-3",
            "language_config": {
                "languages": ["vi", "en"],
                "code_switching": True,
            },
            "pre_processing": {
                "speech_threshold": 0.8,
                "audio_enhancer": False,
            },
            "endpointing": 3,
            "maximum_duration_without_endpointing": 15,
            "realtime_processing": {
                "custom_vocabulary": False,
                "custom_spelling": False,
                "translation": False,
                "named_entity_recognition": True,
                "sentiment_analysis": True,
            },
            "callback": False,
            "messages_config": {
                "receive_partial_transcripts": True,
                "receive_final_transcripts": True,
                "receive_speech_events": True,
                "receive_pre_processing_events": True,
                "receive_post_processing_events": True,
                "receive_acknowledgments": True,
                "receive_lifecycle_events": True,
            },
        }

    async def transcribe(
        self,
        audio: bytes,
        language: str,
        hotwords: Optional[list[str]] = None,
        primary_language: Optional[str] = None,
    ) -> TranscriptionResult:
        del language, hotwords, primary_language
        headers = {
            "x-gladia-key": settings.GLADIA_API_KEY,
            "Content-Type": "application/json",
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=settings.STT_PROVIDER_TIMEOUT
        )

        try:
            response = await client.post(
                f"{settings.GLADIA_API_BASE_URL.rstrip('/')}/live",
                headers=headers,
                json=self.build_session_config(),
            )
            response.raise_for_status()
            websocket_url = response.json().get("url")
            if not websocket_url:
                raise VoiceProviderException(
                    "Gladia Live session returned no WebSocket URL"
                )
            return await asyncio.wait_for(
                self._stream_audio(websocket_url, audio),
                timeout=settings.STT_PROVIDER_TIMEOUT,
            )
        except VoiceProviderException:
            raise
        except asyncio.TimeoutError as exc:
            raise VoiceProviderException(
                f"Gladia STT timed out after {settings.STT_PROVIDER_TIMEOUT:g}s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            raise VoiceProviderException(
                f"Gladia STT HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise VoiceProviderException(f"Gladia STT failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    async def _stream_audio(
        self, websocket_url: str, audio: bytes
    ) -> TranscriptionResult:
        try:
            import websockets
        except ImportError as exc:
            raise VoiceProviderException(
                "Gladia STT requires the 'websockets' package"
            ) from exc

        final_parts: list[str] = []
        confidences: list[float] = []
        detected_languages: list[str] = []
        aggregated_text = ""

        try:
            async with websockets.connect(
                websocket_url,
                open_timeout=settings.STT_PROVIDER_TIMEOUT,
                close_timeout=5,
                max_size=None,
            ) as socket:
                for offset in range(0, len(audio), _AUDIO_CHUNK_BYTES):
                    await socket.send(audio[offset : offset + _AUDIO_CHUNK_BYTES])
                await socket.send(json.dumps({"type": "stop_recording"}))

                async for raw_message in socket:
                    message = json.loads(raw_message)
                    message_type = message.get("type")
                    if message_type == "error" or message.get("error"):
                        raise VoiceProviderException(
                            f"Gladia Live error: {message.get('error') or message}"
                        )
                    if message_type == "transcript":
                        data = message.get("data") or {}
                        if data.get("is_final"):
                            utterance = data.get("utterance") or {}
                            text = (utterance.get("text") or "").strip()
                            if text:
                                final_parts.append(text)
                            if utterance.get("confidence") is not None:
                                confidences.append(float(utterance["confidence"]))
                            if utterance.get("language"):
                                detected_languages.append(utterance["language"])
                    elif message_type == "post_final_transcript":
                        aggregated_text = (
                            message.get("data", {})
                            .get("transcription", {})
                            .get("full_transcript", "")
                            .strip()
                        )
                    elif message_type == "end_session":
                        break
        except VoiceProviderException:
            raise
        except Exception as exc:
            raise VoiceProviderException(
                f"Gladia Live WebSocket failed: {exc}"
            ) from exc

        text = aggregated_text or " ".join(final_parts).strip()
        if not text:
            raise VoiceProviderException("Gladia STT returned an empty transcript")
        confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )
        return TranscriptionResult(
            text=text,
            language=detected_languages[0] if detected_languages else "auto",
            confidence=max(0.0, min(1.0, confidence)),
            stt_provider="gladia",
        )
