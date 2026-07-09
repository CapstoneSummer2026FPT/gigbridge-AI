import logging
from app.api.schemas.job_posts import JobPostGenerationRequest, JobPostGenerationResponse
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.memory import MemoryManager, get_memory_manager
from app.prompts.manager import PromptManager, get_prompt_manager
from app.core.exceptions import AIServerException

logger = logging.getLogger("ai_server.job_posts_service")

def is_vietnamese(text: str) -> bool:
    vietnamese_chars = set("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ")
    return any(char in vietnamese_chars for char in text)

class JobPostService:
    """Service handling AI-assisted job description writing workflows"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        memory_manager: MemoryManager = get_memory_manager(),
        prompt_manager: PromptManager = get_prompt_manager(),
        rag_service = None
    ):
        self.llm = llm_gateway
        self.memory = memory_manager
        self.prompt = prompt_manager
        from app.services.rag import get_rag_service
        self.rag = rag_service or get_rag_service()

    async def generate_job_description(self, request: JobPostGenerationRequest) -> JobPostGenerationResponse:
        logger.info("Generating job description using RAG pipeline")
        
        from app.api.schemas.rag import AnswerConfig, RetrievalGroup

        target_lang = "Vietnamese" if is_vietnamese(request.client_prompt) else "English"

        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Review the client's questions and the lists of allowed database fields. "
            "Select the single best matching Major ID and Category ID. "
            "Identify matching System Skill IDs and supply relevant custom skills if needed.\n"
            "SAFETY POLICY:\n"
            "- You MUST NOT generate job posts for illegal, harmful, or dangerous jobs (e.g., selling illegal substances/drugs, weapons, violence, hacking/cyberattacks, human trafficking, fraud, etc.).\n"
            "- If the client's prompt requests any such illegal activity, you MUST return title='POLICY_VIOLATION' and set the other fields as specified in the template.\n"
            "LANGUAGE CONSTRAINTS:\n"
            f"- You MUST generate BOTH the 'description' and 'question_recruitment' fields strictly in {target_lang}.\n"
            "- All other fields (specifically 'title' and 'custom_skills') MUST ALWAYS be generated in English, regardless of the prompt's language."
        )

        config = AnswerConfig(
            style="fast",
            collection_name="ai-create-job-post",
            response_format=JobPostGenerationResponse,
            retrieval_groups=[
                RetrievalGroup(name="majors", n_results=10, where={"type": "major"}),
                RetrievalGroup(name="categories", n_results=15, where={"type": "category"}),
                RetrievalGroup(name="skills", n_results=30, where={"type": "skill"}),
            ],
            system_prompt=system_prompt,
            user_template="job_posts.txt"
        )

        # Invoke unified configuration-driven RAG answering flow
        result = await self.rag.answer_question(request.client_prompt, config)
        
        response_data = result.answer

        # If LLM generation fell back to string due to parsing error, raise exception
        if isinstance(response_data, str):
            logger.error(f"Failed to parse job description structured output: {response_data}")
            raise AIServerException(
                message="The model generated an invalid job description response structure.",
                status_code=500,
                errors=["invalid_response_structure"]
            )

        # Check for policy violation sentinel
        if response_data.title == "POLICY_VIOLATION":
            logger.warning(f"Safety policy violation detected in prompt: {request.client_prompt}")
            raise AIServerException(
                message="The request violates platform safety guidelines against illegal or harmful activities.",
                status_code=400,
                errors=["policy_violation"]
            )

        # Ensure total skills (system + custom) do not exceed 10, prioritizing system skills
        total_system = len(response_data.system_skill_ids)
        if total_system > 10:
            response_data.system_skill_ids = response_data.system_skill_ids[:10]
            response_data.custom_skills = []
        elif total_system + len(response_data.custom_skills) > 10:
            response_data.custom_skills = response_data.custom_skills[:(10 - total_system)]

        # Map system skill IDs to names to maintain backward-compatible combined `skills` list in memory cache
        skill_id_to_name = {}
        for src in result.sources:
            meta = src.get("metadata", {})
            if meta.get("type") == "skill" and "skill_id" in meta and "name" in meta:
                skill_id_to_name[meta["skill_id"]] = meta["name"]

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
