"""
PURPOSE: Unified facade module for candidate talent matching and freelancer job matching.
IMPORTANCE: Critical — Primary entrypoint for matching domain services across API routes and test suites.
READING FLOW: app/schemas/matching.py -> app/services/matching/matching_base.py -> app/services/matching/job_matching.py -> app/services/matching/freelancer_matching.py -> app/services/matching/__init__.py
"""

from typing import Optional
from app.services.matching.matching_base import MatchingBaseService
from app.services.matching.job_matching import JobMatchingService
from app.services.matching.freelancer_matching import FreelancerMatchingService
from app.services.matching.phonetic_matcher import PhoneticMatcher
from app.services.matching.typo_matcher import TypoMatcher
from app.core.config import settings
from app.schemas.matching import (
    TalentRerankRequest,
    TalentRerankResponse,
    TalentRerankMatch,
    JobRerankRequest,
    JobRerankResponse,
    JobRerankMatch,
)
from app.services.rag import RAGService, get_rag_service
from app.clients.db.chroma import ChromaDBClient, get_chroma_client


class MatchingService(MatchingBaseService):
    """Facade class composing JobMatchingService, FreelancerMatchingService, PhoneticMatcher, and TypoMatcher."""

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
    ):
        """Initialize MatchingService facade with underlying specialized matching services."""
        super().__init__(rag_service=rag_service, chroma_client=chroma_client)
        self.job_matcher = JobMatchingService(rag_service=self.rag, chroma_client=self.chroma)
        self.freelancer_matcher = FreelancerMatchingService(rag_service=self.rag, chroma_client=self.chroma)
        self.phonetic_matcher = PhoneticMatcher()
        self.typo_matcher = TypoMatcher()

    async def rerank_talent(self, request: TalentRerankRequest) -> TalentRerankResponse:
        """Delegate candidate talent reranking for a job post."""
        if settings.ENABLE_MOCK_AI:
            savings_pattern = [15.0, 8.0, 18.0, 5.0, 12.0, 20.0]
            matches = [
                TalentRerankMatch(
                    freelancer_id=c.freelancer_id,
                    embedding_score=round(92.5 - idx * 0.4, 1),
                    algorithm_score=round(95.0 - idx * 0.5, 1),
                    semantic_strengths=["Matched primary skill", "High availability"],
                    match_reasons=["Verified contract match"],
                    saving_percentage=savings_pattern[idx % len(savings_pattern)],
                    budget_bonus=savings_pattern[idx % len(savings_pattern)],
                ) for idx, c in enumerate(request.candidates[:request.top_k])
            ]
            return TalentRerankResponse(
                algorithm_version="2.0-mock",
                embedding_model="mock-embedding-v1",
                scoring_version="mock-scoring-v1",
                matches=matches
            )
        return await self.job_matcher.rerank_talent(request)

    async def rerank_jobs_for_freelancer(self, request: JobRerankRequest) -> JobRerankResponse:
        """Delegate job post reranking for a freelancer."""
        if settings.ENABLE_MOCK_AI:
            matches = [
                JobRerankMatch(
                    job_id=c.job_id,
                    embedding_score=91.0,
                    algorithm_score=93.5,
                    semantic_strengths=["Strong domain alignment"],
                    match_reasons=["Skill overlap"]
                ) for c in request.candidates[:request.top_k]
            ]
            return JobRerankResponse(
                algorithm_version="2.0-mock",
                embedding_model="mock-embedding-v1",
                scoring_version="mock-scoring-v1",
                matches=matches
            )
        return await self.freelancer_matcher.rerank_jobs_for_freelancer(request)


def get_matching_service() -> MatchingService:
    """Dependency injection helper returning a singleton/fresh instance of MatchingService."""
    return MatchingService()
