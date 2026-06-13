import logging
from app.api.schemas.job_posts import JobPostGenerationRequest, JobPostGenerationResponse
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.memory import MemoryManager, get_memory_manager

logger = logging.getLogger("ai_server.job_posts_service")

class JobPostService:
    """Service handling AI-assisted job description writing workflows"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        memory_manager: MemoryManager = get_memory_manager()
    ):
        self.llm = llm_gateway
        self.memory = memory_manager

    async def generate_job_description(self, request: JobPostGenerationRequest) -> JobPostGenerationResponse:
        logger.info(f"Generating job description for title: {request.title}")
        
        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Structure your output in markdown, including sections: **About the Role**, **Key Responsibilities**, **Requirements**, and **What We Offer**.\n"
            "Adhere to the requested skills and context provided."
        )

        user_prompt = (
            f"Please generate a job post description for the following position:\n"
            f"Title: {request.title}\n"
            f"Category: {request.category}\n"
            f"Required Skills: {', '.join(request.skills) if request.skills else 'None specified'}\n"
        )
        if request.additional_context:
            user_prompt += f"Company Context / Extra Details: {request.additional_context}\n"

        # Call LLM Gateway
        raw_markdown = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # Cache this job post context in memory for subsequent matches
        job_id = f"job_post_gen_{request.title.lower().replace(' ', '_')}"
        await self.memory.save_domain_context("job_posts", job_id, {
            "title": request.title,
            "category": request.category,
            "skills": request.skills,
            "description": raw_markdown
        })

        return JobPostGenerationResponse(
            description=raw_markdown,
            is_ai_generated=True
        )

# Dependency helper
def get_job_post_service() -> JobPostService:
    return JobPostService()
