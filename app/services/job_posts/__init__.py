"""
PURPOSE: Unified facade module for AI job description generation, taxonomy matching, and milestone hiring plans.
IMPORTANCE: Critical — Primary entrypoint for job post domain services across API routes and test suites.
READING FLOW: app/schemas/job_posts.py -> app/services/job_posts/job_post_base.py -> app/services/job_posts/job_details_generator.py -> app/services/job_posts/hiring_plan_generator.py -> app/services/job_posts/__init__.py
"""

from typing import Optional
from app.schemas.job_posts import (
    JobPostDetailsGenerationResponse,
    JobPostGenerationRequest,
    JobPostHiringPlanGenerationRequest,
    JobPostHiringPlanGenerationResponse,
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.prompts.manager import PromptManager, get_prompt_manager
from app.services.rag import RAGService, get_rag_service
from app.services.job_posts.job_post_base import JobPostBaseService
from app.services.job_posts.job_details_generator import JobDetailsGeneratorService
from app.services.job_posts.hiring_plan_generator import HiringPlanGeneratorService


class JobPostService(JobPostBaseService):
    """Facade composing JobDetailsGeneratorService and HiringPlanGeneratorService."""

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        prompt_manager: Optional[PromptManager] = None,
        rag_service: Optional[RAGService] = None,
    ):
        """Initialize JobPostService facade with underlying specialized services."""
        super().__init__(llm_gateway=llm_gateway, prompt_manager=prompt_manager, rag_service=rag_service)
        self.details_generator = JobDetailsGeneratorService(
            llm_gateway=self.llm, prompt_manager=self.prompt, rag_service=self.rag
        )
        self.hiring_plan_generator = HiringPlanGeneratorService(
            llm_gateway=self.llm, prompt_manager=self.prompt, rag_service=self.rag
        )

    async def generate_job_details(
        self, request: JobPostGenerationRequest
    ) -> JobPostDetailsGenerationResponse:
        """Delegate job details generation."""
        return await self.details_generator.generate_job_details(request)

    async def generate_job_hiring_plan(
        self, request: JobPostHiringPlanGenerationRequest
    ) -> JobPostHiringPlanGenerationResponse:
        """Delegate job hiring plan generation."""
        return await self.hiring_plan_generator.generate_job_hiring_plan(request)


def get_job_post_service() -> JobPostService:
    """Dependency injection helper returning instance of JobPostService."""
    return JobPostService()


from app.services.job_posts.analysis import AnalysisService, get_analysis_service

