from typing import List, Optional
from pydantic import BaseModel, Field

class TalentMatchingRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job post to match talent for")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of matches to return")
    location_preference: Optional[str] = Field(default=None, description="Preferred work model: 'remote' or 'onsite'")
    min_experience_level: Optional[str] = Field(default=None, description="Minimum experience level")

class TalentMatchResult(BaseModel):
    freelancer_id: str = Field(..., description="Matched freelancer user ID")
    full_name: str = Field(..., description="Full name of freelancer")
    title: str = Field(..., description="Professional title")
    match_score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    match_reasons: List[str] = Field(..., description="Key reasoning points for matching")
    skills_matched: List[str] = Field(..., description="Skills matching the job description")
    skills_missing: List[str] = Field(..., description="Skills requested by the job description but missing from profile")

class TalentMatchingResponse(BaseModel):
    job_id: str = Field(..., description="Target job post ID")
    matches: List[TalentMatchResult] = Field(..., description="Sorted list of best-matching candidates")
