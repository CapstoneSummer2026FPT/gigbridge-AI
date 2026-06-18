import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    AI_SERVER_API_KEY: str = Field(default="dev-key-please-change-in-env")
    MAX_INTERVIEW_QUESTIONS: int = 3

    # LLM API Keys
    OPENAI_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")
    CLAUDE_API_KEY: str = Field(default="")
    ELEVENLABS_API_KEY: str = Field(default="")

    # LLM Router Configurations
    DEFAULT_LLM_PROVIDER: str = Field(default="gemini")
    LOCAL_OLLAMA_URL: str = Field(default="http://localhost:11434")
    LOCAL_MODEL_NAME: str = Field(default="llama3.2")

    # RAG Settings
    CHROMA_DB_PATH: str = Field(default="./chroma_db")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-large")

    # ── Voice Provider Settings ──────────────────────────────────
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_SESSION_TTL: int = 3600           # 60 minutes
    REDIS_DRAFT_TTL: int = 600              # 10 minutes
    REDIS_TTS_CACHE_TTL: int = 900          # 15 minutes
    REDIS_HISTORY_TTL: int = 7200           # 2 hours

    # STT
    STT_PRIMARY_PROVIDER: str = Field(default="google")
    STT_FALLBACK_PROVIDER: str = Field(default="faster_whisper")
    FASTER_WHISPER_MODEL: str = Field(default="base")
    FASTER_WHISPER_DEVICE: str = Field(default="cpu")
    FASTER_WHISPER_COMPUTE_TYPE: str = Field(default="int8")

    # Audio Decode — ALL formats decoded to WAV 16kHz mono PCM before STT
    AUDIO_DECODE_SAMPLE_RATE: int = 16000

    # TTS
    TTS_PRIMARY_PROVIDER: str = Field(default="edge_tts")
    TTS_FALLBACK_PROVIDER: str = Field(default="google")
    EDGE_TTS_TIMEOUT: int = 5               # seconds
    EDGE_TTS_VOICE_VI: str = Field(default="vi-VN-HoaiMyNeural")
    EDGE_TTS_VOICE_EN: str = Field(default="en-US-JennyNeural")

    # Audio Validation
    AUDIO_MAX_SIZE_BYTES: int = 3_145_728   # 3 MB
    AUDIO_MAX_DURATION_SECONDS: int = 90    # max recording length
    AUDIO_SILENCE_THRESHOLD: float = 0.02   # RMS threshold (numpy)
    ACCEPTED_AUDIO_TYPES: list = Field(default_factory=lambda: [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/wav",
        "audio/mpeg",
        "audio/mp4",
    ])

    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
