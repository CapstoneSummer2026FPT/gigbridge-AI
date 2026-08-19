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
from app.schemas.matching import (
    TalentRerankRequest,
    TalentRerankResponse,
    JobRerankRequest,
    JobRerankResponse,
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
        return await self.job_matcher.rerank_talent(request)

    async def rerank_jobs_for_freelancer(self, request: JobRerankRequest) -> JobRerankResponse:
        """Delegate job post reranking for a freelancer."""
        return await self.freelancer_matcher.rerank_jobs_for_freelancer(request)


def get_matching_service() -> MatchingService:
    """Dependency injection helper returning a singleton/fresh instance of MatchingService."""
    return MatchingService()
