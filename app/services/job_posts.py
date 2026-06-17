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
        
        # Build category ID to name map for parent name resolution
        id_to_name = {cat.categories_id: cat.name for cat in request.allowed_categories}
        
        # Create resolved category payload with parent name strings
        resolved_categories = []
        for cat in request.allowed_categories:
            parent_name = id_to_name.get(cat.parent_category_id) if cat.parent_category_id else None
            resolved_categories.append({
                "categories_id": cat.categories_id,
                "name": cat.name,
                "is_active": cat.is_active,
                "parent_category_name": parent_name
            })
            
        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Analyze the client's questions to infer the job title, job category, major, required skills, and write a detailed job description.\n"
            "The job description must be in markdown format, containing sections: **About the Role**, **Key Responsibilities**, **Requirements**, and **What We Offer**."
        )

        user_prompt = self.prompt.render_prompt("job_posts.txt", {
            "client_questions": request.client_questions,
            "allowed_categories": resolved_categories
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
            "major": response_data.major,
            "category": response_data.category_name,  # for backward compatibility
            "category_id": response_data.category_id,
            "category_name": response_data.category_name,
            "skills": response_data.skills,
            "client_questions": request.client_questions,
            "description": response_data.description
        })

        return response_data

# Dependency helper
def get_job_post_service() -> JobPostService:
    return JobPostService()

