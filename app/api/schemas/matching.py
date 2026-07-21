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
    match_reasons: List[str] = Field(default_factory=list, description="Key reasoning points for matching")
    skills_matched: List[str] = Field(default_factory=list, description="Skills matching the job description")
    skills_missing: List[str] = Field(default_factory=list, description="Skills requested by the job description but missing from profile")

class TalentMatchingResponse(BaseModel):
    job_id: str = Field(..., description="Target job post ID")
    matches: List[TalentMatchResult] = Field(default_factory=list, description="Sorted list of best-matching candidates")

# --- Reranking DTOs matching .NET Backend AiServiceClient ---

class TalentRerankJob(BaseModel):
    job_id: str = Field(..., description="Job Post ID")
    title: str = Field(..., description="Job Title")
    description: str = Field(default="", description="Job Description")
    industry: Optional[str] = Field(default=None, description="Industry or Category")
    skills: List[str] = Field(default_factory=list, description="List of required skills")

class TalentRerankCandidate(BaseModel):
    freelancer_id: str = Field(..., description="Freelancer Profile ID")
    title: Optional[str] = Field(default=None, description="Freelancer Title")
    bio: Optional[str] = Field(default=None, description="Freelancer Profile Bio")
    skills: List[str] = Field(default_factory=list, description="Freelancer Skills")
    work_history: List[str] = Field(default_factory=list, description="Work experience history summaries")
    deterministic_score: float = Field(default=0.0, description="Deterministic base score from backend")

class TalentRerankRequest(BaseModel):
    job: TalentRerankJob = Field(..., description="Job Post details")
    candidates: List[TalentRerankCandidate] = Field(default_factory=list, description="Shortlist of candidate profiles to evaluate")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of top reranked matches to return")

class TalentRerankMatch(BaseModel):
    freelancer_id: str = Field(..., description="Matched freelancer profile ID")
    semantic_score: float = Field(..., description="Semantic RAG score between 0.0 and 1.0")
    match_reasons: List[str] = Field(default_factory=list, description="LLM rationale for candidate evaluation")
    skills_matched: List[str] = Field(default_factory=list, description="Candidate skills matching job requirements")
    skills_missing: List[str] = Field(default_factory=list, description="Required job skills missing from candidate profile")

class TalentRerankResponse(BaseModel):
    matches: List[TalentRerankMatch] = Field(default_factory=list, description="Reranked list of candidates")
