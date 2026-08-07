"""Shared data models for the voice processing subsystem.

These types are used across the entire voice pipeline — from the abstract engine
interfaces in stt_engine/ and tts_engine/, through the gateway and session layer,
up to the facade and API routes.
"""

from dataclasses import dataclass
from enum import Enum


# ──────────────────────────────────────────────
# Error Codes
# ──────────────────────────────────────────────

class VoiceErrorCode(str, Enum):
    """Stable error codes returned to the frontend. Never rename or renumber."""
    SESSION_NOT_FOUND = "session_not_found"
    DRAFT_EXPIRED = "draft_expired"
    NO_SPEECH_DETECTED = "no_speech_detected"
    UPLOAD_TOO_LARGE = "upload_too_large"
    UNSUPPORTED_AUDIO_TYPE = "unsupported_audio_type"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONFIRM_CONFLICT = "confirm_conflict"
    DRAFT_INDEX_MISMATCH = "draft_index_mismatch"
    AUDIO_DECODE_FAILED = "audio_decode_failed"
    AUDIO_TOO_LONG = "audio_too_long"
    INVALID_LANGUAGE = "invalid_language"


# ──────────────────────────────────────────────
# Language support
# ──────────────────────────────────────────────

class Language(str, Enum):
    VIETNAMESE = "vi"
    VIETNAMESE_FULL = "vi-VN"
    ENGLISH = "en"
    ENGLISH_FULL = "en-US"

    @classmethod
    def parse(cls, value: str) -> "Language":
        """Normalize a BCP-47 language code to a known Language value.
        Accepts 'vi', 'vi-VN', 'en', 'en-US', 'vi_vn', etc."""
        if not value:
            return cls.VIETNAMESE  # default
        normalized = value.lower().replace("_", "-")[:5]
        if normalized.startswith("vi"):
            return cls.VIETNAMESE
        elif normalized.startswith("en"):
            return cls.ENGLISH
        raise ValueError(f"Unsupported language: {value}")

    def stt_hint(self) -> str:
        """Language hint passed to STT engines (e.g. 'vi', 'en')."""
        return self.value[:2]

    def tts_code(self) -> str:
        """Full BCP-47 code for TTS voice selection (e.g. 'vi-VN', 'en-US')."""
        return {"vi": "vi-VN", "en": "en-US"}[self.value[:2]]


# ──────────────────────────────────────────────
# STT result
# ──────────────────────────────────────────────

@dataclass
class TranscriptionResult:
    """Result returned by any STT engine after successful transcription.

    Engines MUST raise VoiceProviderException on failure — never return a
    degraded/empty TranscriptionResult. The gateway catches exceptions and
    chains to the fallback provider.
    """
    text: str
    language: str
    confidence: float
    stt_provider: str
    fallback_used: bool = False


# ──────────────────────────────────────────────
# TTS result
# ──────────────────────────────────────────────

@dataclass
class SynthesisResult:
    """Result returned by any TTS engine after successful synthesis.

    Same contract as TranscriptionResult: raise on failure, never degrade.
    """
    audio_bytes: bytes
    mime_type: str
    tts_provider: str
    fallback_used: bool = False


# ──────────────────────────────────────────────
# Draft data (stored as JSON in Redis)
# ──────────────────────────────────────────────

@dataclass
class DraftData:
    """A confirmed transcription draft stored in Redis.

    Stored as JSON under draft:{session_id} with a 10-minute TTL.
    The question_index field allows the confirm step to verify the draft
    matches the session's current question (prevents off-by-one bugs).
    """
    draft_id: str
    question_index: int
    transcript: str
    language: str
    stt_provider: str
    confidence: float
    created_at: str
    confirmed: bool = False


# ──────────────────────────────────────────────
# Session state (stored as Redis hash)
# ──────────────────────────────────────────────

@dataclass
class InterviewSession:
    """In-memory representation of a voice interview session.

    The source of truth is the Redis hash session:{session_id}.
    This dataclass is populated from Redis on load_or_expire() calls.
    """
    session_id: str
    job_id: str
    freelancer_id: str
    mode: str
    language: str
    question_index: int
    question_count: int = 3
    stt_language: str = ""
    job_title: str = ""
    job_description: str = ""
    job_skills: list[str] | None = None
    hotwords: list[str] | None = None
    job_phonetic_aliases: dict[str, list[str]] | None = None
    job_questions: list[str] | None = None


# ──────────────────────────────────────────────
# History entry (appended to Redis list)
# ──────────────────────────────────────────────

@dataclass
class HistoryEntry:
    """A single turn in the interview conversation history.

    Stored as JSON in the Redis list session:{session_id}:history.
    """
    role: str  # "user" | "assistant"
    content: str
    language: str
