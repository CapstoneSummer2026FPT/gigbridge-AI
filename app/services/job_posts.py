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
        logger.info("Generating job description")
        
        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Review the client's questions and the lists of allowed database fields. "
            "Select the single best matching Major ID and Category ID. "
            "Identify matching System Skill IDs and supply relevant custom skills if needed."
        )

        user_prompt = self.prompt.render_prompt("job_posts.txt", {
            "client_prompt": request.client_prompt,
            "allowed_majors": request.allowed_majors,
            "allowed_categories": request.allowed_categories,
            "available_skills": request.available_skills
        })

        # Call LLM Gateway with response_format to get structured JSON output
        response_json = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=JobPostGenerationResponse
        )

        # Parse structured response
        response_data = JobPostGenerationResponse.model_validate_json(response_json)

        # Ensure total skills (system + custom) do not exceed 10, prioritizing system skills
        total_system = len(response_data.system_skill_ids)
        if total_system > 10:
            response_data.system_skill_ids = response_data.system_skill_ids[:10]
            response_data.custom_skills = []
        elif total_system + len(response_data.custom_skills) > 10:
            response_data.custom_skills = response_data.custom_skills[:(10 - total_system)]

        # Map system skill IDs to names to maintain backward-compatible combined `skills` list in memory cache
        skill_id_to_name = {s.skill_id: s.name for s in request.available_skills}
        combined_skills = [
            skill_id_to_name[sid] for sid in response_data.system_skill_ids if sid in skill_id_to_name
        ] + response_data.custom_skills

        # Cache this job post context in memory for subsequent matches
        job_id = f"job_post_gen_{response_data.title.lower().replace(' ', '_')}"
        await self.memory.save_domain_context("job_posts", job_id, {
            "title": response_data.title,
            "major_id": response_data.major_id,
            "category_id": response_data.category_id,
            "skills": combined_skills,  # For backward-compatible matching service
            "system_skill_ids": response_data.system_skill_ids,
            "custom_skills": response_data.custom_skills,
            "client_prompt": request.client_prompt,
            "question_recruitment": response_data.question_recruitment,
            "description": response_data.description
        })

        return response_data

# Dependency helper
def get_job_post_service() -> JobPostService:
    return JobPostService()

