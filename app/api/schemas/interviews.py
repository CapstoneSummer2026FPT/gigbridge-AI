from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ── Request Schemas ─────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job post being applied for")
    freelancer_id: str = Field(..., description="ID of the freelancer candidate")
    job_title: str = Field(..., min_length=1, description="Title from the job post")
    job_description: Optional[str] = Field(
        None, description="Job post description or requirements summary"
    )
    job_skills: List[str] = Field(
        default_factory=list,
        description="Required skills, tools, technologies, or keywords from the job post",
    )
    job_phonetic_aliases: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Optional job-scoped phonetic aliases keyed by canonical term",
    )
    mode: str = Field(default="text", description="Interview mode: 'text' or 'voice'")
    language: str = Field(default="auto", description="Primary BCP-47 language code (auto, vi, en)")


class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Active interview session identifier")
    answer_text: str = Field(..., description="User answered transcript or text response")


class ConfirmAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Active interview session identifier")
    corrected_text: Optional[str] = Field(
        None, description="Optional corrected transcript if the STT was inaccurate"
    )


# ── Response Schemas ────────────────────────────────────────────

class InterviewFeedback(BaseModel):
    score: int = Field(..., description="Overall score out of 100")
    summary: str = Field(..., description="Summary of candidate performance")
    technical_skills: List[str] = Field(..., description="Assessed technical skills")
    soft_skills: List[str] = Field(..., description="Assessed communication/soft skills")
    recommended_hire: bool = Field(..., description="Final hiring recommendation")


class InterviewQuestionResponse(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    question_index: int = Field(..., description="Index number of current question")
    question_text: Optional[str] = Field(None, description="Current question text")
    language: Optional[str] = Field(None, description="BCP-47 language code")
    audio_base64: Optional[str] = Field(
        None, description="Base64 encoded TTS audio data"
    )
    audio_mime_type: Optional[str] = Field(
        None, description="MIME type of the audio (e.g. audio/mpeg)"
    )
    tts_provider: Optional[str] = Field(
        None, description="TTS provider used (edge_tts, google_tts, cache)"
    )
    fallback_used: bool = Field(
        default=False, description="Whether a fallback provider was used"
    )
    is_completed: bool = Field(
        default=False, description="True if interview is finished"
    )
    feedback: Optional[InterviewFeedback] = Field(
        None, description="Grading feedback if completed"
    )


class DraftDataResponse(BaseModel):
    """Response from the transcribe-audio endpoint (before confirmation)."""
    session_id: str = Field(..., description="Session identifier")
    draft_id: str = Field(..., description="Draft identifier for the transcription")
    question_index: int = Field(..., description="Question index this draft belongs to")
    transcript: str = Field(..., description="Corrected transcript text from STT")
    language: str = Field(..., description="Detected or requested language")
    stt_provider: str = Field(..., description="STT provider used (google_stt, faster_whisper)")
    confidence: float = Field(..., description="Confidence score (0.0–1.0)")
    fallback_used: bool = Field(
        default=False, description="Whether a fallback STT provider was used"
    )
    expires_at: str = Field(
        ..., description="ISO timestamp when this draft expires"
    )
