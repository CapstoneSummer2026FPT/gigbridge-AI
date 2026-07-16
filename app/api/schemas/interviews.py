from typing import Annotated, Literal, Optional, List, Dict
from pydantic import BaseModel, Field, StringConstraints, field_validator


SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{8,128}$"

SessionId = Annotated[
    str,
    StringConstraints(pattern=SESSION_ID_PATTERN),
]


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
    mode: Literal["text", "voice"] = Field(default="text", description="Interview mode")
    language: Literal["auto", "vi", "en"] = Field(
        default="auto", description="Primary interview language"
    )


class SubmitAnswerRequest(BaseModel):
    session_id: SessionId = Field(..., description="Active interview session identifier")
    answer_text: str = Field(..., description="User answered transcript or text response")


class ConfirmAnswerRequest(BaseModel):
    session_id: SessionId = Field(..., description="Active interview session identifier")
    corrected_text: Optional[str] = Field(
        None, description="Optional corrected transcript if the STT was inaccurate"
    )

    @field_validator("corrected_text")
    @classmethod
    def reject_blank_corrected_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("answer_text_required")
        return value


# ── Response Schemas ────────────────────────────────────────────

class QuestionAnswerPair(BaseModel):
    question_index: int = Field(..., description="1-indexed question identifier")
    question_text: str = Field(..., description="The text of the question asked")
    candidate_answer: str = Field(..., description="The answer provided by the candidate")


class AnalyzeVettingRequest(BaseModel):
    freelancer_id: str = Field(..., description="The ID of the freelancer candidate")
    job_title: str = Field(..., min_length=1, description="Title from the job post")
    job_description: Optional[str] = Field(None, description="Job post requirements/description")
    job_skills: List[str] = Field(default_factory=list, description="Required skills from the job post")
    qa_pairs: List[QuestionAnswerPair] = Field(..., description="Questions and answers to analyze")


class GradedQuestion(BaseModel):
    question_index: int = Field(..., description="1-indexed question identifier")
    question_text: str = Field(..., description="The question text asked")
    question_type: Literal["theoretical", "problem_solving"] = Field(..., description="Question classification")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="Difficulty rating")
    candidate_answer: str = Field(..., description="The raw answer provided by the candidate")
    score: int = Field(..., ge=0, le=100, description="Score on a scale of 0 to 100")
    feedback: str = Field(..., description="Short justification highlighting strengths and gaps")


class InterviewFeedback(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Overall score out of 100")
    summary: str = Field(..., description="Summary of candidate performance")
    technical_skills: List[str] = Field(..., description="Assessed technical skills")
    soft_skills: List[str] = Field(..., description="Assessed communication/soft skills")
    recommended_hire: bool = Field(..., description="Final hiring recommendation")
    holistic_adjustment: int = Field(default=0, ge=-15, le=15, description="Holistic score modifier (-15 to +15)")
    holistic_adjustment_reason: str = Field(default="", description="Explanation for the holistic adjustment")
    graded_questions: List[GradedQuestion] = Field(default_factory=list, description="List of individual question grades and details")


class InterviewQuestionResponse(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    audio_access_token: Optional[str] = Field(
        None, description="Bearer token required to retrieve this session's TTS audio"
    )
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
        None, description="TTS provider used (elevenlabs, edge_tts, google_tts, cache)"
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
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    fallback_used: bool = Field(
        default=False, description="Whether a fallback STT provider was used"
    )
    expires_at: str = Field(
        ..., description="ISO timestamp when this draft expires"
    )


class QuestionAudioResponse(BaseModel):
    """Lazy TTS audio polling response."""
    session_id: str = Field(..., description="Session identifier")
    question_index: int = Field(..., description="Question index")
    status: str = Field(..., description="pending, ready, failed, or missing")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio when ready")
    audio_mime_type: Optional[str] = Field(None, description="MIME type when ready")
    tts_provider: Optional[str] = Field(None, description="Provider used when ready")
    fallback_used: bool = Field(default=False, description="Whether fallback TTS was used")
    error: Optional[str] = Field(None, description="Failure reason when status is failed")
