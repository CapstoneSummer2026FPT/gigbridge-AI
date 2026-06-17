from typing import List, Optional
from pydantic import BaseModel, Field



class JobPostGenerationRequest(BaseModel):
    client_questions: List[str] = Field(
        default=[],
        description="A list of questions designed to verify whether the candidate understands the job requirements."
    )

class JobPostGenerationResponse(BaseModel):
    title: str = Field(..., description="The job title")
    major: str = Field(..., description="The major or field of the job")
    category: str = Field(..., description="The job category")
    skills : List[str] = Field(..., description="A list of required skills for the job")
    description: str = Field(..., description="Generated job description in markdown format")
    is_ai_generated: bool = Field(default=True, description="Indicates the description was AI-generated")
