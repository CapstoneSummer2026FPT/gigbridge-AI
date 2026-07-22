from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

from pydantic import Field, model_validator

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    APP_ENV: Literal["development", "test", "production"] = "production"
    AI_SERVER_API_KEY: str = Field(default="")
    MAX_INTERVIEW_QUESTIONS: int = 3

    # Paid endpoint rate limits (SlowAPI format)
    RATE_LIMIT_START: str = "30/minute"
    RATE_LIMIT_SUBMIT: str = "60/minute"
    RATE_LIMIT_CONFIRM: str = "60/minute"
    RATE_LIMIT_TRANSCRIBE: str = "30/minute"

    # LLM API Keys
    OPENAI_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")
    CLAUDE_API_KEY: str = Field(default="")
    ELEVENLABS_API_KEY: str = Field(default="")

    # LLM Router Configurations
    DEFAULT_LLM_PROVIDER: str = Field(default="openai")
    LOCAL_OLLAMA_URL: str = Field(default="http://localhost:11434")
    LOCAL_MODEL_NAME: str = Field(default="llama3.2")

    # RAG Settings
    CHROMA_DB_PATH: str = Field(default="./chroma_db")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-large")

    # Smart talent matching uses one embedding model and a deterministic scorer.
    MATCHING_EMBEDDING_PROVIDER: Literal["openai", "gemini", "ollama"] = Field(
        default="openai"
    )
    MATCHING_EMBEDDING_MODEL: str = Field(default="text-embedding-3-large")
    MATCHING_SCORING_VERSION: str = Field(default="weighted-features-v1")
    MATCHING_ALGORITHM_VERSION: str = Field(default="2.0")
    MATCHING_RETRIEVAL_LIMIT: int = Field(default=50, ge=1, le=100)
    MATCHING_RERANK_LIMIT: int = Field(default=50, ge=1, le=50)

    # ── Voice Provider Settings ──────────────────────────────────
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_SESSION_TTL: int = 3600           # 60 minutes
    REDIS_DRAFT_TTL: int = 600              # 10 minutes
    REDIS_TTS_CACHE_TTL: int = 900          # 15 minutes
    REDIS_HISTORY_TTL: int = 7200           # 2 hours

    # STT
    STT_PRIMARY_PROVIDER: str = Field(default="faster_whisper")
    STT_FALLBACK_PROVIDER: str = Field(default="google")
    STT_PROVIDER_TIMEOUT: float = Field(default=30.0)
    FASTER_WHISPER_MODEL: str = Field(default="base")
    FASTER_WHISPER_DEVICE: str = Field(default="cpu")
    FASTER_WHISPER_COMPUTE_TYPE: str = Field(default="int8")
    FASTER_WHISPER_CHUNK_SECONDS: int = Field(default=30)
    FASTER_WHISPER_CHUNK_OVERLAP_SECONDS: int = Field(default=2)
    GOOGLE_STT_HOTWORD_BOOST: float = Field(default=5.0)

    # Audio Decode — ALL formats decoded to WAV 16kHz mono PCM before STT
    AUDIO_DECODE_SAMPLE_RATE: int = 16000

    # TTS
    TTS_PRIMARY_PROVIDER: str = Field(default="edge_tts")
    TTS_FALLBACK_PROVIDER: str = Field(default="google")
    TTS_PROVIDER_TIMEOUT: float = Field(default=120.0)
    TTS_CHUNK_CHARS: int = Field(default=220)
    TTS_BATCH_CONCURRENCY: int = Field(default=1)
    EDGE_TTS_TIMEOUT: int = 15               # seconds
    EDGE_TTS_MULTILINGUAL_VOICE: str = Field(default="en-US-AvaMultilingualNeural")
    EDGE_TTS_VOICE_VI: str = Field(default="vi-VN-HoaiMyNeural")
    EDGE_TTS_VOICE_EN: str = Field(default="en-US-JennyNeural")
    ELEVENLABS_MODEL: str = Field(default="eleven_multilingual_v2")
    ELEVENLABS_OUTPUT_FORMAT: str = Field(default="mp3_44100_128")
    ELEVENLABS_VOICE_ID: str = Field(default="")
    ELEVENLABS_VOICE_ID_VI: str = Field(default="")
    ELEVENLABS_VOICE_ID_EN: str = Field(default="")
    TTS_STITCH_SAMPLE_RATE: int = Field(default=24000)
    TTS_STITCH_CROSSFADE_MS: int = Field(default=35)
    TTS_STITCH_PEAK: float = Field(default=0.95)
    VIENEU_SAMPLE_RATE: int = Field(default=48000)
    VIENEU_VOICE_ID: str = Field(default="")

    # Audio Validation
    AUDIO_MAX_SIZE_BYTES: int = 3_145_728   # 3 MB
    AUDIO_MAX_DURATION_SECONDS: int = 90    # max recording length
    AUDIO_SILENCE_THRESHOLD: float = 0.02   # RMS threshold (numpy)
    ACCEPTED_AUDIO_TYPES: list[str] = Field(default_factory=lambda: [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/wav",
        "audio/mpeg",
        "audio/mp4",
    ])

    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="")

    # Hugging Face Hub
    HF_TOKEN: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_server_api_key(self) -> "Settings":
        """Reject missing/public placeholder credentials outside explicit dev/test."""
        insecure_values = {
            "",
            "dev-key-please-change-in-env",
            "your-secure-shared-api-key-here",
        }
        if (
            self.APP_ENV == "production"
            and self.AI_SERVER_API_KEY.strip() in insecure_values
        ):
            raise ValueError(
                "AI_SERVER_API_KEY must be set to a non-placeholder value in production"
            )
        return self


settings = Settings()
