import logging
from app.api.schemas.job_posts import JobPostGenerationRequest, JobPostGenerationResponse
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.memory import MemoryManager, get_memory_manager
from app.prompts.manager import PromptManager, get_prompt_manager


logger = logging.getLogger("ai_server.job_posts_service")

class JobPostService:
    """Service handling AI-assisted job description writing workflows"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        memory_manager: MemoryManager = get_memory_manager(),
        prompt_manager: PromptManager = get_prompt_manager()
    ):
        self.llm = llm_gateway
        self.memory = memory_manager
        self.prompt = prompt_manager

    async def generate_job_description(self, request: JobPostGenerationRequest) -> JobPostGenerationResponse:
        logger.info(f"Generating job description from {len(request.client_questions)} client questions")
        
        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Analyze the client's questions to infer the job title, job category, required skills, and write a detailed job description.\n"
            "The job description must be in markdown format, containing sections: **About the Role**, **Key Responsibilities**, **Requirements**, and **What We Offer**."
        )

        user_prompt = self.prompt.render_prompt("job_posts.txt", {
            "client_questions": request.client_questions
        })

        # Call LLM Gateway with response_format to get structured JSON output
        response_json = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=JobPostGenerationResponse
        )

        # Parse structured response
        response_data = JobPostGenerationResponse.model_validate_json(response_json)

        # Cache this job post context in memory for subsequent matches
        job_id = f"job_post_gen_{response_data.title.lower().replace(' ', '_')}"
        await self.memory.save_domain_context("job_posts", job_id, {
            "title": response_data.title,
            "category": response_data.catgory,
            "skills": response_data.skills,
            "client_questions": request.client_questions,
            "description": response_data.description
        })

        return response_data

# Dependency helper
def get_job_post_service() -> JobPostService:
    return JobPostService()

