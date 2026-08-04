import logging
import re
from app.api.schemas.job_posts import (
    JobPostGenerationRequest,
    JobPostDetailsGenerationResponse,
    JobPostHiringPlanGenerationRequest, JobPostHiringPlanGenerationResponse
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.memory import MemoryManager, get_memory_manager
from app.prompts.manager import PromptManager, get_prompt_manager
from app.core.exceptions import AIServerException

import datetime

logger = logging.getLogger("ai_server.job_posts_service")

def convert_date_to_iso(date_str: str) -> str:
    if not date_str:
        return date_str
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str

def is_vietnamese(text: str) -> bool:
    # 1. Check for accented Vietnamese characters
    vietnamese_chars = set("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ")
    if any(char in vietnamese_chars for char in text):
        return True

    # 2. Check for uniquely Vietnamese unaccented words/syllables
    # These are words common in Vietnamese text (specifically job posts) and do not exist in English.
    uniquely_vietnamese = {
        "tuyen", "trinh", "vien", "thiet", "phan", "mem", "phat", "trien", "yeu",
        "nghiem", "luong", "tuyendung", "khoi", "chuc", "danh", "cong", "nghe",
        "khach", "quan", "tai", "chinh", "toan", "dich", "thuat", "xay", "kien",
        "truc", "truyen", "vietnam", "viec", "dung", "giup", "tro", "viet"
    }
    
    text_lower = text.lower()
    
    # Check for multi-word phrases first
    for phrase in ["tuyen dung", "lap trinh", "phat trien", "kinh nghiem", "yeu cau", 
                   "thiet ke", "phan mem", "he thong", "lam viec", "cong ty", "du an", 
                   "nhan su", "tai chinh", "ke toan", "ban hang", "dich vu", "ky thuat", 
                   "xay dung", "kien truc", "do hoa"]:
        if phrase in text_lower:
            return True
            
    # Tokenize and check if any word is uniquely Vietnamese
    words = re.findall(r"\b[a-z]+\b", text_lower)
    if any(w in uniquely_vietnamese for w in words):
        return True
        
    return False



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

    async def generate_job_details(self, request: JobPostGenerationRequest) -> JobPostDetailsGenerationResponse:
        logger.info("Generating job details using RAG pipeline")
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
            f"- You MUST generate the 'description' field strictly in {target_lang}.\n"
            "- All other fields (specifically 'title' and 'custom_skills') MUST ALWAYS be generated in English, regardless of the prompt's language."
        )

        config = AnswerConfig(
            style="precision",
            collection_name="ai-create-job-post",
            response_format=JobPostDetailsGenerationResponse,
            retrieval_groups=[
                RetrievalGroup(name="majors", n_results=10, where={"type": "major"}),
                RetrievalGroup(name="categories", n_results=15, where={"type": "category"}),
                RetrievalGroup(name="skills", n_results=15, where={"type": "skill"}),
            ],
            system_prompt=system_prompt,
            user_template="job_posts_details.txt"
        )

        result = await self.rag.answer_question(request.client_prompt, config)
        response_data = result.answer

        if isinstance(response_data, str):
            logger.error(f"Failed to parse job details structured output: {response_data}")
            raise AIServerException(
                message="The model generated an invalid job description response structure.",
                status_code=500,
                errors=["invalid_response_structure"]
            )

        if response_data.title == "POLICY_VIOLATION":
            logger.warning(f"Safety policy violation detected in prompt: {request.client_prompt}")
            raise AIServerException(
                message="The request violates platform safety guidelines against illegal or harmful activities.",
                status_code=400,
                errors=["policy_violation"]
            )

        total_system = len(response_data.system_skill_ids)
        if total_system > 10:
            response_data.system_skill_ids = response_data.system_skill_ids[:10]
            response_data.custom_skills = []
        elif total_system + len(response_data.custom_skills) > 10:
            response_data.custom_skills = response_data.custom_skills[:(10 - total_system)]

        return response_data

    async def generate_job_hiring_plan(self, request: JobPostHiringPlanGenerationRequest) -> JobPostHiringPlanGenerationResponse:
        logger.info("Generating job hiring plan using RAG pipeline")
        from app.api.schemas.rag import AnswerConfig

        target_lang = "Vietnamese" if is_vietnamese(request.client_prompt) else "English"

        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional milestone plans and vetting questions for their projects.\n"
            "SAFETY POLICY:\n"
            "- You MUST NOT generate hiring plans for illegal, harmful, or dangerous jobs.\n"
            "- If the provided context indicates illegal activity, you MUST return empty lists for question_recruitment and milestones.\n"
            "LANGUAGE CONSTRAINTS:\n"
            f"- You MUST generate all text fields (vetting questions and milestone fields) strictly in {target_lang}."
        )

        combined_prompt = (
            f"Original user requirement:\n{request.client_prompt}\n\n"
            f"Generated/Approved Job Details:\n"
            f"Title: {request.title}\n"
            f"Description: {request.description}"
        )

        config = AnswerConfig(
            style="precision",
            collection_name="ai-create-job-post",
            response_format=JobPostHiringPlanGenerationResponse,
            retrieval_groups=[],
            system_prompt=system_prompt,
            user_template="job_posts_hiring_plan.txt"
        )

        result = await self.rag.answer_question(combined_prompt, config)
        response_data = result.answer

        if isinstance(response_data, str):
            logger.error(f"Failed to parse hiring plan structured output: {response_data}")
            raise AIServerException(
                message="The model generated an invalid hiring plan response structure.",
                status_code=500,
                errors=["invalid_response_structure"]
            )

        if response_data.milestones:
            for milestone in response_data.milestones:
                milestone.due_date = convert_date_to_iso(milestone.due_date)

        compulsory_question = "Bạn có bao nhiêu kinh nghiệm cho vai trò này?" if target_lang == "Vietnamese" else "How many experiences do you have for this role?"
        raw_questions = response_data.question_recruitment or []
        filtered_questions = [
            q for q in raw_questions
            if "how many experiences" not in q.lower() and "bao nhiêu kinh nghiệm" not in q.lower()
        ]
        response_data.question_recruitment = filtered_questions[:3] + [compulsory_question]

        return response_data

# Dependency helper
def get_job_post_service() -> JobPostService:
    return JobPostService()
