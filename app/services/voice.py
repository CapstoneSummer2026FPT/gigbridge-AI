import io
import httpx
import base64
import logging
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger("ai_server.voice_service")

class VoiceService:
    """Service handling speech synthesis (TTS via ElevenLabs) and audio transcription (STT via Whisper)"""
    
    def __init__(self):
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.stt_client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        
        # ElevenLabs default voice configuration (Rachel voice ID)
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.default_voice_id}"

    async def text_to_speech(self, text: str) -> Optional[str]:
        """
        Synthesizes text into speech audio and returns a base64-encoded string.
        """
        if not self.elevenlabs_api_key:
            logger.warning("ElevenLabs API Key is not configured. Skipping TTS generation.")
            return None

        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "content-type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.tts_url, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"ElevenLabs TTS failed: Status {response.status_code}, {response.text}")
                    return None
                
                # Convert binary audio content to base64
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                return audio_base64
        except Exception as e:
            logger.error(f"TTS generation error: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, filename: str) -> str:
        """
        Transcribes candidate audio files using OpenAI's Whisper model.
        """
        if not self.stt_client:
            raise ValueError("OpenAI API Key is not configured for transcription (Whisper).")

        try:
            # Create a file-like buffer from bytes
            audio_buffer = io.BytesIO(audio_bytes)
            audio_buffer.name = filename  # Whisper requires a filename parameter to detect format

            logger.info(f"Sending audio file {filename} for Whisper transcription")
            response = await self.stt_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer
            )
            return response.text
        except Exception as e:
            logger.error(f"Whisper transcription failed: {str(e)}")
            raise ValueError(f"Transcription failed: {str(e)}")

# Dependency helper
_voice_service = VoiceService()

def get_voice_service() -> VoiceService:
    return _voice_service
