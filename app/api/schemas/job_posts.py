from typing import List, Optional
from pydantic import BaseModel, Field

class JobPostGenerationRequest(BaseModel):
    title: str = Field(..., description="Job title, e.g., Senior React Developer")
    category: str = Field(..., description="Job category, e.g., Web Development")
    skills: List[str] = Field(default=[], description="List of required skill tags")
    additional_context: Optional[str] = Field(default=None, description="Optional extra descriptions or company details")

class JobPostGenerationResponse(BaseModel):
    description: str = Field(..., description="Generated job description in markdown format")
    is_ai_generated: bool = Field(default=True, description="Indicates the description was AI-generated")
