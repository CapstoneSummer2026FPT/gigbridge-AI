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


class TalentRerankVerifiedWork(BaseModel):
    contract_id: str
    title: str
    description: Optional[str] = None
    major_name: Optional[str] = None
    category_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)


class TalentRerankJob(BaseModel):
    job_id: str
    title: str
    description: str = ""
    industry: Optional[str] = None
    major_id: Optional[str] = None
    major_name: Optional[str] = None
    major_category_id: Optional[str] = None
    category_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    custom_skills: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    estimated_duration: Optional[str] = None


class TalentRerankCandidate(BaseModel):
    freelancer_id: str
    title: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    availability: int = 0
    major_id: Optional[str] = None
    major_name: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    verified_work: List[TalentRerankVerifiedWork] = Field(default_factory=list)


class TalentRerankRequest(BaseModel):
    job: TalentRerankJob
    candidates: List[TalentRerankCandidate] = Field(min_length=1, max_length=100)
    top_k: int = Field(default=10, ge=1, le=30)
    algorithm_version: str = "2.0"
    scoring_version: str = "weighted-features-v1"


class TalentRerankMatch(BaseModel):
    freelancer_id: str
    embedding_score: float = Field(ge=0, le=100)
    algorithm_score: float = Field(ge=0, le=100)
    match_reasons: List[str] = Field(default_factory=list)
    semantic_strengths: List[str] = Field(default_factory=list)


class TalentRerankResponse(BaseModel):
    matches: List[TalentRerankMatch]
    algorithm_version: str
    embedding_model: str
    scoring_version: str
