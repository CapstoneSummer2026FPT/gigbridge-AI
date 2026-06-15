from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionAnswerPair(BaseModel):
    question: str = Field(..., description="The client's question")
    answer: str = Field(..., description="The freelancer's answer")

class JobPostGenerationRequest(BaseModel):
    title: str = Field(..., description="Job title, e.g., Senior React Developer")
    category: str = Field(..., description="Job category, e.g., Web Development")
    skills: List[str] = Field(default=[], description="List of required skill tags")
    client_questions_and_freelancer_answers: List[QuestionAnswerPair] = Field(
        default=[],
        description="A list of question and answer pairs designed to verify whether the candidate understands the job requirements."
    )

class JobPostGenerationResponse(BaseModel):
    description: str = Field(..., description="Generated job description in markdown format")
    is_ai_generated: bool = Field(default=True, description="Indicates the description was AI-generated")
