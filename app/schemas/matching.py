"""
PURPOSE: Pydantic data contracts for candidate talent matching and freelancer job reranking.
IMPORTANCE: Critical — Defines payload structures for embedding vector search and deterministic algorithm reranking.
READING FLOW: app/schemas/matching.py -> app/services/matching/matching_base.py -> app/services/matching/* -> app/api/routes/matching.py
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Deprecated legacy recommendation contract. Production matching uses /matching/rerank.
class TalentMatchingRequest(StrictModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)
    location_preference: Optional[str] = Field(default=None, max_length=100)
    min_experience_level: Optional[str] = Field(default=None, max_length=100)


class TalentMatchResult(StrictModel):
    freelancer_id: str
    full_name: str
    title: str
    match_score: float
    match_reasons: List[str] = Field(default_factory=list)
    skills_matched: List[str] = Field(default_factory=list)
    skills_missing: List[str] = Field(default_factory=list)


class TalentMatchingResponse(StrictModel):
    job_id: str
    matches: List[TalentMatchResult] = Field(default_factory=list)


class TalentRerankJob(StrictModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    industry: Optional[str] = Field(default=None, max_length=200)
    major_id: Optional[str] = Field(default=None, max_length=100)
    major_name: Optional[str] = Field(default=None, max_length=200)
    major_category_id: Optional[str] = Field(default=None, max_length=100)
    category_name: Optional[str] = Field(default=None, max_length=200)
    skills: List[str] = Field(default_factory=list, max_length=100)
    custom_skills: List[str] = Field(default_factory=list, max_length=100)
    location: Optional[str] = Field(default=None, max_length=300)
    estimated_duration: Optional[str] = Field(default=None, max_length=100)


class TalentRerankVerifiedWork(StrictModel):
    contract_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=500)
    major_name: Optional[str] = Field(default=None, max_length=200)
    category_name: Optional[str] = Field(default=None, max_length=200)
    skills: List[str] = Field(default_factory=list, max_length=100)


class TalentRerankCandidate(StrictModel):
    freelancer_id: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, max_length=300)
    bio: Optional[str] = Field(default=None, max_length=1200)
    location: Optional[str] = Field(default=None, max_length=300)
    availability: int = Field(..., ge=0, le=1)
    major_id: Optional[str] = Field(default=None, max_length=100)
    major_name: Optional[str] = Field(default=None, max_length=200)
    categories: List[str] = Field(default_factory=list, max_length=30)
    skills: List[str] = Field(default_factory=list, max_length=100)
    verified_work: List[TalentRerankVerifiedWork] = Field(default_factory=list, max_length=5)


class TalentRerankRequest(StrictModel):
    job: TalentRerankJob
    candidates: List[TalentRerankCandidate] = Field(default_factory=list, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    algorithm_version: str = Field(default="2.0", min_length=1, max_length=64)
    scoring_version: str = Field(default="weighted-features-v1", min_length=1, max_length=64)


class TalentRerankMatch(StrictModel):
    freelancer_id: str
    embedding_score: float = Field(..., ge=0, le=100)
    algorithm_score: float = Field(..., ge=0, le=100)
    semantic_strengths: List[str] = Field(default_factory=list, max_length=5)
    match_reasons: List[str] = Field(default_factory=list, max_length=3)


class TalentRerankResponse(StrictModel):
    algorithm_version: str
    embedding_model: str
    scoring_version: str
    matches: List[TalentRerankMatch] = Field(default_factory=list)


# --- Freelancer -> Job matching ("browse jobs" recommendation) ---

class JobRerankVerifiedWork(StrictModel):
    contract_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=500)
    major_name: Optional[str] = Field(default=None, max_length=200)
    category_name: Optional[str] = Field(default=None, max_length=200)
    skills: List[str] = Field(default_factory=list, max_length=100)


class JobRerankFreelancer(StrictModel):
    freelancer_id: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = Field(default=None, max_length=300)
    bio: Optional[str] = Field(default=None, max_length=1200)
    location: Optional[str] = Field(default=None, max_length=300)
    availability: int = Field(..., ge=0, le=1)
    major_id: Optional[str] = Field(default=None, max_length=100)
    major_name: Optional[str] = Field(default=None, max_length=200)
    categories: List[str] = Field(default_factory=list, max_length=30)
    skills: List[str] = Field(default_factory=list, max_length=100)
    verified_work: List[JobRerankVerifiedWork] = Field(default_factory=list, max_length=5)


class JobRerankCandidate(StrictModel):
    job_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    industry: Optional[str] = Field(default=None, max_length=200)
    major_id: Optional[str] = Field(default=None, max_length=100)
    major_name: Optional[str] = Field(default=None, max_length=200)
    major_category_id: Optional[str] = Field(default=None, max_length=100)
    category_name: Optional[str] = Field(default=None, max_length=200)
    skills: List[str] = Field(default_factory=list, max_length=100)
    custom_skills: List[str] = Field(default_factory=list, max_length=100)
    location: Optional[str] = Field(default=None, max_length=300)
    estimated_duration: Optional[str] = Field(default=None, max_length=100)


class JobRerankRequest(StrictModel):
    freelancer: JobRerankFreelancer
    candidates: List[JobRerankCandidate] = Field(default_factory=list, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    algorithm_version: str = Field(default="2.0", min_length=1, max_length=64)
    scoring_version: str = Field(default="weighted-features-v1", min_length=1, max_length=64)


class JobRerankMatch(StrictModel):
    job_id: str
    embedding_score: float = Field(..., ge=0, le=100)
    algorithm_score: float = Field(..., ge=0, le=100)
    semantic_strengths: List[str] = Field(default_factory=list, max_length=5)
    match_reasons: List[str] = Field(default_factory=list, max_length=3)


class JobRerankResponse(StrictModel):
    algorithm_version: str
    embedding_model: str
    scoring_version: str
    matches: List[JobRerankMatch] = Field(default_factory=list)
