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
from datetime import date, timedelta
from math import ceil

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

# ---------------------------------------------------------------------------
# Duration unit helpers
# ---------------------------------------------------------------------------

# Approximate conversion factors to weeks
_WEEKS_PER_UNIT: dict[str, float] = {
    "week": 1.0,
    "weeks": 1.0,
    "tuần": 1.0,
    "month": 4.333,
    "months": 4.333,
    "tháng": 4.333,
    "year": 52.0,
    "years": 52.0,
    "năm": 52.0,
}


def parse_duration_to_weeks(duration_str: str) -> float:
    """Parse a human-readable duration string (e.g. '2 weeks', '1 month', '3 tháng')
    and return the equivalent number of weeks as a float.
    Returns 0.0 if the string cannot be parsed.
    """
    if not duration_str:
        return 0.0
    parts = duration_str.strip().split()
    if len(parts) < 2:
        return 0.0
    try:
        value = float(parts[0])
    except ValueError:
        return 0.0
    unit = parts[1].lower().rstrip(".")
    factor = _WEEKS_PER_UNIT.get(unit, 0.0)
    return value * factor


def format_weeks_to_duration(weeks: float) -> str:
    """Convert a week count back to a human-readable duration string.
    Always uses 'weeks' as the unit to keep things simple and parseable.
    Minimum is 1 week.
    """
    w = max(1, round(weeks))
    return f"{w} week" if w == 1 else f"{w} weeks"


# ---------------------------------------------------------------------------
# Post-generation correction helpers
# ---------------------------------------------------------------------------


def _clamp_milestone_budgets(milestones: list, approved_budget: float) -> None:
    """Scale milestone amounts so they sum to EXACTLY approved_budget.
    Operates in-place. No-op when approved_budget <= 0 or list is empty.
    """
    if not milestones or approved_budget <= 0:
        return

    approved_budget = round(approved_budget, 2)
    total = sum(m.amount for m in milestones)
    if total <= 0:
        # Distribute evenly when LLM produced zeros or non-positive amounts
        per = round(approved_budget / len(milestones), 2)
        for m in milestones:
            m.amount = per
        milestones[-1].amount = round(
            approved_budget - sum(m.amount for m in milestones[:-1]), 2
        )
        return

    # Proportional scaling
    scale = approved_budget / total
    for m in milestones[:-1]:
        m.amount = round(m.amount * scale, 2)

    # Assign exact remainder to last milestone to absorb any decimal rounding drift
    milestones[-1].amount = round(
        approved_budget - sum(m.amount for m in milestones[:-1]), 2
    )
    if milestones[-1].amount < 0:
        milestones[-1].amount = 0.0


def _clamp_milestone_durations(milestones: list, approved_weeks: float) -> None:
    """Scale milestone estimated_duration strings so their total equals EXACTLY
    approved_weeks. Operates in-place. No-op when approved_weeks <= 0.
    """
    if not milestones or approved_weeks <= 0:
        return

    target_weeks = max(len(milestones), round(approved_weeks))
    individual_weeks = [
        max(1.0, parse_duration_to_weeks(m.estimated_duration)) for m in milestones
    ]
    total_weeks = sum(individual_weeks)

    if total_weeks <= 0:
        per = max(1, target_weeks // len(milestones))
        for m in milestones:
            m.estimated_duration = format_weeks_to_duration(per)
        rem = target_weeks - (per * (len(milestones) - 1))
        milestones[-1].estimated_duration = format_weeks_to_duration(max(1, rem))
        return

    # Scale proportionally
    scaled_weeks = []
    for mw in individual_weeks[:-1]:
        w = max(1, round(mw * target_weeks / total_weeks))
        scaled_weeks.append(w)

    last_w = target_weeks - sum(scaled_weeks)
    if last_w < 1:
        # Rebalance if last milestone gets less than 1 week
        needed = 1 - last_w
        last_w = 1
        for i in range(len(scaled_weeks) - 1, -1, -1):
            if scaled_weeks[i] > 1:
                deduct = min(needed, scaled_weeks[i] - 1)
                scaled_weeks[i] -= deduct
                needed -= deduct
                if needed <= 0:
                    break

    scaled_weeks.append(last_w)

    for m, w in zip(milestones, scaled_weeks):
        m.estimated_duration = format_weeks_to_duration(w)


def _recalculate_due_dates(milestones: list, start: date) -> None:
    """Recalculate due_date for every milestone sequentially from *start*,
    based on each milestone's (possibly corrected) estimated_duration.
    Dates are stored in ISO 'YYYY-MM-DD' format.
    """
    current = start
    for m in milestones:
        weeks = parse_duration_to_weeks(m.estimated_duration)
        days = ceil(weeks * 7)
        current = current + timedelta(days=days)
        m.due_date = current.strftime("%Y-%m-%d")

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


def _strip_budget_and_timeline_sections(text: str) -> str:
    """Removes any standalone Budget, Timeline, or Compensation section headers
    and bullet lines from the generated description text body, keeping core sections intact.
    """
    if not text:
        return text

    # Pattern 1: Section headers and everything until the next uppercase section header or end of text
    budget_timeline_section_pattern = re.compile(
        r"(?m)^\s*(?:BUDGET|ESTIMATED BUDGET|TIMELINE|ESTIMATED DURATION|DURATION|BUDGET & TIMELINE|BUDGET AND TIMELINE|COMPENSATION|NGÂN SÁCH|THỜI GIAN DỰ KIẾN)\s*$\n.*?(?=\n\s*[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĐ][A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĐ\s]{2,}\s*$|\Z)",
        re.DOTALL | re.IGNORECASE
    )
    cleaned = budget_timeline_section_pattern.sub("", text)

    # Pattern 2: Standalone bullet lines mentioning estimated budget, duration, or salary in GigCoins
    budget_timeline_line_pattern = re.compile(
        r"(?m)^\s*[-•*]?\s*(?:Estimated budget|Estimated duration|Budget|Duration|Ngân sách|Thời gian|Competitive salary in GigCoins|Lương cạnh tranh|Mức lương).*$\n?",
        re.IGNORECASE
    )
    cleaned = budget_timeline_line_pattern.sub("", cleaned)

    # Clean up double blank lines / trailing whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned



def resolve_canonical_budget(budget_min: float | None, budget_max: float | None) -> float:
    """Calculates the integer-rounded average budget if both min and max are present,
    or falls back to max / min if only one is provided.
    """
    b_min = float(budget_min) if (budget_min is not None and float(budget_min) > 0) else None
    b_max = float(budget_max) if (budget_max is not None and float(budget_max) > 0) else None
    if b_min is not None and b_max is not None:
        return float(round((b_min + b_max) / 2.0))
    if b_max is not None:
        return float(round(b_max))
    if b_min is not None:
        return float(round(b_min))
    return 0.0


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
            f"- You MUST generate both the 'title' and 'description' fields strictly in {target_lang}.\n"
            "- Custom skills can be in English or Vietnamese matching the prompt context."
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

        # Sanitize description text to strip redundant budget and timeline sections
        if response_data.description:
            response_data.description = _strip_budget_and_timeline_sections(response_data.description)

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

        approved_budget = resolve_canonical_budget(request.budget_min, request.budget_max)
        approved_weeks = parse_duration_to_weeks(request.estimated_duration or "")

        # Build explicit numeric constraint block so the LLM has exact targets
        constraint_block = (
            f"\n\nHARD CONSTRAINTS — these are code-enforced and must not be violated:\n"
            f"- Total milestone budget MUST sum to EXACTLY {approved_budget:.2f} GC"
            f" (budget_min={request.budget_min}, budget_max={request.budget_max})\n"
            f"- Total milestone duration MUST NOT exceed {approved_weeks:.1f} weeks"
            f" ({request.estimated_duration})\n"
            f"- Each individual milestone duration must be expressed as 'N weeks' (integer only)."
        )

        combined_prompt = (
            f"Original user requirement:\n{request.client_prompt}\n\n"
            f"Generated/Approved Job Details:\n"
            f"Title: {request.title}\n"
            f"Description: {request.description}\n"
            f"Approved Budget: {approved_budget:.2f} GC\n"
            f"Approved Duration: {request.estimated_duration}"
            f"{constraint_block}"
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
            # Step 1: Normalise any mm/dd/yyyy due_dates from the LLM to ISO
            for milestone in response_data.milestones:
                milestone.due_date = convert_date_to_iso(milestone.due_date)

            # Step 2: Deterministic budget enforcement — scale amounts so they
            # sum to exactly the approved budget regardless of LLM output.
            _clamp_milestone_budgets(response_data.milestones, approved_budget)

            # Step 3: Deterministic duration enforcement — scale durations so
            # total weeks never exceeds the approved project timeline.
            _clamp_milestone_durations(response_data.milestones, approved_weeks)

            # Step 4: Recalculate due dates sequentially starting strictly from current day (today).
            start_date = date.today()
            _recalculate_due_dates(response_data.milestones, start_date)

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
