from typing import Optional, List
from pydantic import BaseModel, Field

class StartInterviewRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job post being applied for")
    freelancer_id: str = Field(..., description="ID of the freelancer candidate")
    mode: str = Field(default="text", description="Interview interface mode: 'text' or 'voice'")

class SubmitAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Active interview session identifier")
    answer_text: str = Field(..., description="User answered transcript or text response")

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
    audio_base64: Optional[str] = Field(None, description="Base64 encoded TTS audio data (ElevenLabs)")
    is_completed: bool = Field(default=False, description="True if interview is finished")
    feedback: Optional[InterviewFeedback] = Field(None, description="Grading feedback if completed")
