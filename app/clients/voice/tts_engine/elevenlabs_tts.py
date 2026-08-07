"""ElevenLabs Text-to-Speech engine."""

import asyncio
import json
import socket
from urllib import error, parse, request

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.tts_engine.base import BaseTTSEngine
from app.clients.voice.models import SynthesisResult


class ElevenLabsTTSEngine(BaseTTSEngine):
    """ElevenLabs TTS engine using the HTTP API."""

    def __init__(self):
        if not settings.ELEVENLABS_API_KEY:
            raise VoiceProviderException("ELEVENLABS_API_KEY not configured")

    async def synthesize(self, text: str, language: str) -> SynthesisResult:
        """Synthesize text to audio via ElevenLabs."""
        voice_id = self._voice_id_for(language)
        query = parse.urlencode({"output_format": settings.ELEVENLABS_OUTPUT_FORMAT})
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
        payload = {
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL,
        }
        normalized_language = (language or "").strip().lower()[:2]
        if normalized_language in {"vi", "en"}:
            payload["language_code"] = normalized_language

        try:
            audio_bytes = await asyncio.to_thread(self._post_json, url, payload)
        except TimeoutError:
            raise VoiceProviderException(
                f"ElevenLabs TTS timed out after {settings.TTS_PROVIDER_TIMEOUT:.0f}s"
            )
        except error.HTTPError as exc:
            detail = self._error_detail(exc)
            raise VoiceProviderException(
                f"ElevenLabs TTS failed with {exc.code}: {detail}"
            )
        except error.URLError as exc:
            raise VoiceProviderException(f"ElevenLabs TTS request failed: {exc}")

        if not audio_bytes:
            raise VoiceProviderException("ElevenLabs TTS returned empty audio")

        return SynthesisResult(
            audio_bytes=audio_bytes,
            mime_type=self._mime_type_for(settings.ELEVENLABS_OUTPUT_FORMAT),
            tts_provider="elevenlabs",
        )

    @staticmethod
    def _post_json(url: str, payload: dict) -> bytes:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            headers={
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        try:
            with request.urlopen(
                req,
                timeout=settings.TTS_PROVIDER_TIMEOUT,
            ) as response:
                return response.read()
        except socket.timeout as exc:
            raise TimeoutError from exc

    @staticmethod
    def _voice_id_for(language: str) -> str:
        normalized = (language or "").lower()[:2]
        if normalized == "vi" and settings.ELEVENLABS_VOICE_ID_VI:
            return settings.ELEVENLABS_VOICE_ID_VI
        if normalized == "en" and settings.ELEVENLABS_VOICE_ID_EN:
            return settings.ELEVENLABS_VOICE_ID_EN
        return settings.ELEVENLABS_VOICE_ID

    @staticmethod
    def _mime_type_for(output_format: str) -> str:
        if output_format.startswith("wav_"):
            return "audio/wav"
        if output_format.startswith("pcm_"):
            return "audio/L16"
        return "audio/mpeg"

    @staticmethod
    def _error_detail(exc: error.HTTPError) -> str:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text[:300]
        return str(data)[:300]
