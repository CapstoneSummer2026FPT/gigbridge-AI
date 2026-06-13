import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    AI_SERVER_API_KEY: str = Field(default="dev-key-please-change-in-env")

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
