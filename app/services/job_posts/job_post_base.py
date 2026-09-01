"""
PURPOSE: Job post generation base class and mathematical clamping, date formatting, and text sanitization helpers.
IMPORTANCE: Critical — Core mathematical and post-processing utility layer enforcing budget/duration constraints.
READING FLOW: app/schemas/job_posts.py -> app/services/job_posts/job_post_base.py -> app/services/job_posts/job_details_generator.py -> app/services/job_posts/hiring_plan_generator.py
"""

import datetime
from datetime import date, timedelta
import logging
from math import ceil
import re
from typing import Any, Dict, List, Optional

from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.prompts.manager import PromptManager, get_prompt_manager
from app.services.rag import RAGService, get_rag_service

logger = logging.getLogger("ai_server.job_post_base")

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

VIETNAMESE_CHARS = set("ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵĐ")
UNIQUELY_VIETNAMESE_WORDS = {
    "tuyen", "trinh", "vien", "thiet", "phan", "mem", "phat", "trien", "yeu",
    "nghiem", "luong", "tuyendung", "khoi", "chuc", "danh", "cong", "nghe",
    "khach", "quan", "tai", "chinh", "toan", "dich", "thuat", "xay", "kien",
    "truc", "truyen", "vietnam", "viec", "dung", "giup", "tro", "viet"
}

_TAXONOMY_CACHE: Dict[str, Any] = {"majors": [], "categories": [], "categories_by_major": {}, "skills": []}


def get_full_taxonomy() -> Dict[str, Any]:
    """Load and cache all majors, categories, and skills from categories_skills.jsonl."""
    if _TAXONOMY_CACHE["majors"]:
        return _TAXONOMY_CACHE

    import json
    from pathlib import Path

    paths_to_try = [
        Path("knowledge-base/ai-create-job-post/categories_skills.jsonl"),
        Path(__file__).resolve().parents[2] / "knowledge-base" / "ai-create-job-post" / "categories_skills.jsonl",
        Path(__file__).resolve().parents[3] / "knowledge-base" / "ai-create-job-post" / "categories_skills.jsonl",
    ]

    for p in paths_to_try:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        item = json.loads(line)
                        t = item.get("type")
                        if t == "major":
                            _TAXONOMY_CACHE["majors"].append({"major_id": item["major_id"], "name": item["name"]})
                        elif t == "category":
                            _TAXONOMY_CACHE["categories"].append({"category_id": item["category_id"], "major_id": item["major_id"], "name": item["name"]})
                            m_id = item["major_id"]
                            if m_id not in _TAXONOMY_CACHE["categories_by_major"]:
                                _TAXONOMY_CACHE["categories_by_major"][m_id] = []
                            _TAXONOMY_CACHE["categories_by_major"][m_id].append({"category_id": item["category_id"], "name": item["name"]})
                        elif t == "skill":
                            _TAXONOMY_CACHE["skills"].append({"skill_id": item["skill_id"], "name": item["name"]})
                break
            except Exception as e:
                logger.warning(f"Failed to read taxonomy file {p}: {e}")

    return _TAXONOMY_CACHE



class JobPostBaseService:
    """Base class for job post generation services providing post-processing and clamping math."""

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        prompt_manager: Optional[PromptManager] = None,
        rag_service: Optional[RAGService] = None,
    ):
        """Initialize JobPostBaseService with LLM gateway, prompt manager, and RAG service."""
        self.llm = llm_gateway or get_llm_gateway()
        self.prompt = prompt_manager or get_prompt_manager()
        self.rag = rag_service or get_rag_service()

    @staticmethod
    def is_vietnamese(text: str) -> bool:
        """Detect whether text prompt is written in Vietnamese using diacritics and vocabulary checks."""
        if any(char in VIETNAMESE_CHARS for char in text):
            return True

        text_lower = text.lower()
        for phrase in [
            "tuyen dung", "lap trinh", "phat trien", "kinh nghiem", "yeu cau",
            "thiet ke", "phan mem", "he thong", "lam viec", "cong ty", "du an",
            "nhan su", "tai chinh", "ke toan", "ban hang", "dich vu", "ky thuat",
            "xay dung", "kien truc", "do hoa"
        ]:
            if phrase in text_lower:
                return True

        words = re.findall(r"\b[a-z]+\b", text_lower)
        if any(w in UNIQUELY_VIETNAMESE_WORDS for w in words):
            return True

        return False

    NONSENSE_PROMPT_PATTERNS = {
        "hi", "hihi", "hihihi", "hello", "hey", "chao", "chào", "xin chao", "xin chào",
        "alo", "test", "testing", "asdf", "asdfg", "asdfghjkl", "qwerty", "123", "1234",
        "12345", "123456", "abc", "abcd", "abcxyz", "xxx", "zzz", "aaa", "bbb", "ccc",
        "haha", "hahaha", "hehe", "hehehe", "kkk", "kkkk"
    }

    @classmethod
    def validate_client_prompt(cls, prompt: str) -> None:
        """Validate client prompt for minimum length and meaningless/nonsense content before calling LLM."""
        from app.core.exceptions import AIServerException

        if not prompt or not prompt.strip():
            raise AIServerException(
                message="The prompt provided is invalid or meaningless. Please describe your project requirements in detail.",
                status_code=400,
                errors=["invalid_prompt"]
            )

        clean_prompt = prompt.strip().lower()
        words = re.findall(r"\b\w+\b", clean_prompt)

        if not words:
            raise AIServerException(
                message="The prompt provided is invalid or meaningless. Please describe your project requirements in detail.",
                status_code=400,
                errors=["invalid_prompt"]
            )

        full_text_condensed = "".join(words)
        if len(prompt.strip()) < 8 or len(words) < 2:
            if clean_prompt in cls.NONSENSE_PROMPT_PATTERNS or full_text_condensed in cls.NONSENSE_PROMPT_PATTERNS or len(full_text_condensed) < 5:
                raise AIServerException(
                    message="The prompt provided is invalid or meaningless. Please describe your project requirements in detail.",
                    status_code=400,
                    errors=["invalid_prompt"]
                )

        if clean_prompt in cls.NONSENSE_PROMPT_PATTERNS or full_text_condensed in cls.NONSENSE_PROMPT_PATTERNS:
            raise AIServerException(
                message="The prompt provided is invalid or meaningless. Please describe your project requirements in detail.",
                status_code=400,
                errors=["invalid_prompt"]
            )


    @staticmethod
    def convert_date_to_iso(date_str: str) -> str:
        """Convert date string from various formats (MM/DD/YYYY, YYYY-MM-DD, DD/MM/YYYY) to ISO YYYY-MM-DD."""
        if not date_str:
            return date_str
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str

    @staticmethod
    def parse_duration_to_weeks(duration_str: str) -> float:
        """Parse human-readable duration string (e.g. '2 weeks', '1 month', '3 tháng') into equivalent weeks count."""
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

    @staticmethod
    def format_weeks_to_duration(weeks: float) -> str:
        """Convert float week count into formatted duration string ('N weeks')."""
        w = max(1, round(weeks))
        return f"{w} week" if w == 1 else f"{w} weeks"

    @staticmethod
    def resolve_canonical_budget(budget_min: Optional[float], budget_max: Optional[float]) -> float:
        """Calculate canonical average budget from budget_min and budget_max."""
        b_min = float(budget_min) if (budget_min is not None and float(budget_min) > 0) else None
        b_max = float(budget_max) if (budget_max is not None and float(budget_max) > 0) else None
        if b_min is not None and b_max is not None:
            return float(round((b_min + b_max) / 2.0))
        if b_max is not None:
            return float(round(b_max))
        if b_min is not None:
            return float(round(b_min))
        return 0.0

    @classmethod
    def estimate_milestone_complexity_weights(cls, milestones: list) -> list[float]:
        """Estimate relative complexity weights for milestones based on initial amounts/durations or scope keywords."""
        if not milestones:
            return []

        initial_amounts = [float(getattr(m, "amount", 0.0) or 0.0) for m in milestones]
        initial_durations = [cls.parse_duration_to_weeks(getattr(m, "estimated_duration", "")) for m in milestones]

        max_amt = max(initial_amounts) if initial_amounts else 0.0
        min_amt = min(initial_amounts) if initial_amounts else 0.0
        max_dur = max(initial_durations) if initial_durations else 0.0
        min_dur = min(initial_durations) if initial_durations else 0.0

        if max_amt > 0 and (max_amt / max(1.0, min_amt)) > 1.25:
            return initial_amounts
        if max_dur > 0 and (max_dur / max(0.5, min_dur)) > 1.25:
            return initial_durations

        weights = []
        low_keywords = {
            "setup", "logout", "login", "auth", "outline", "draft", "bug fix", "tweak",
            "config", "export", "data entry", "basic", "cấu hình", "khởi tạo", "đăng xuất",
            "đăng nhập", "dàn trang", "sơ thảo", "nhập liệu"
        }
        high_keywords = {
            "architecture", "sharding", "system design", "engine", "ai", "pipeline",
            "real-time", "high-scale", "infrastructure", "design system", "whitepaper",
            "strategy", "campaign", "valuation", "kiến trúc", "hệ thống lớn", "chiến lược",
            "chuẩn hóa", "tối ưu hóa", "định giá", "tổng thể"
        }

        for m in milestones:
            text = f"{getattr(m, 'title', '')} {getattr(m, 'description', '')}".lower()
            if any(k in text for k in low_keywords) and not any(k in text for k in high_keywords):
                weights.append(1.0)
            elif any(k in text for k in high_keywords):
                weights.append(4.0)
            else:
                weights.append(2.5)

        return weights

    @staticmethod
    def _calculate_budget_rounding_step(approved_budget: float) -> float:
        """Determine an appropriate clean rounding step size based on total budget magnitude."""
        b = float(approved_budget)
        if b <= 50:
            return 1.0
        elif b <= 200:
            return 5.0
        elif b <= 500:
            return 10.0
        elif b <= 2000:
            return 25.0
        elif b <= 5000:
            return 50.0
        elif b <= 20000:
            return 100.0
        else:
            return 500.0

    @classmethod
    def clamp_milestone_budgets(cls, milestones: list, approved_budget: float) -> None:
        """Scale milestone amounts in-place so they sum to exactly approved_budget with clean, rounded numbers."""
        if not milestones or approved_budget <= 0:
            return

        approved_budget = float(round(float(approved_budget)))
        weights = cls.estimate_milestone_complexity_weights(milestones)
        total_weight = sum(weights)

        if total_weight <= 0:
            total_weight = float(len(milestones))
            weights = [1.0] * len(milestones)

        step = cls._calculate_budget_rounding_step(approved_budget)

        for i in range(len(milestones) - 1):
            raw_amt = (weights[i] / total_weight) * approved_budget
            rounded_amt = max(step, round(raw_amt / step) * step)
            milestones[i].amount = float(round(rounded_amt))

        remaining = approved_budget - sum(getattr(m, "amount", 0.0) for m in milestones[:-1])
        if remaining < 0:
            remaining = 0.0
        milestones[-1].amount = float(round(remaining))

    @classmethod
    def clamp_milestone_durations(cls, milestones: list, approved_weeks: float) -> None:
        """Scale milestone estimated_duration strings in-place so total equals approved_weeks according to complexity ratios, merging excess milestones if needed."""
        if not milestones or approved_weeks <= 0:
            return

        individual_weeks = [
            max(1.0, cls.parse_duration_to_weeks(getattr(m, "estimated_duration", ""))) for m in milestones
        ]
        total_weeks = sum(individual_weeks)
        weights = cls.estimate_milestone_complexity_weights(milestones)

        if total_weeks <= approved_weeks:
            if total_weeks == approved_weeks or max(individual_weeks) > min(individual_weeks) or max(weights) == min(weights):
                return

        target_weeks = max(1, round(approved_weeks))

        if len(milestones) > target_weeks:
            keep_count = target_weeks
            last_kept = milestones[keep_count - 1]

            for excess in milestones[keep_count:]:
                if hasattr(last_kept, "amount") and hasattr(excess, "amount"):
                    last_kept.amount = round(float(last_kept.amount or 0) + float(excess.amount or 0), 2)
                for attr in ("title", "description", "deliverables", "acceptance_criteria"):
                    val_kept = getattr(last_kept, attr, "") or ""
                    val_excess = getattr(excess, attr, "") or ""
                    if val_excess and val_excess not in val_kept:
                        combined = f"{val_kept} | {val_excess}" if val_kept else val_excess
                        setattr(last_kept, attr, combined)

            del milestones[keep_count:]
            weights = cls.estimate_milestone_complexity_weights(milestones)

        weights = cls.estimate_milestone_complexity_weights(milestones)
        total_weight = sum(weights) or 1.0

        scaled_weeks = []
        for w_i in weights[:-1]:
            w = max(1, round((w_i / total_weight) * target_weeks))
            scaled_weeks.append(w)

        last_w = target_weeks - sum(scaled_weeks)
        if last_w < 1:
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
            m.estimated_duration = cls.format_weeks_to_duration(w)



    @classmethod
    def recalculate_due_dates(cls, milestones: list, start: date) -> None:
        """Recalculate milestone due_date sequentially starting from start date."""
        current = start
        for m in milestones:
            weeks = cls.parse_duration_to_weeks(getattr(m, "estimated_duration", ""))
            days = ceil(weeks * 7)
            current = current + timedelta(days=days)
            m.due_date = current.strftime("%Y-%m-%d")

    @staticmethod
    def strip_budget_and_timeline_sections(text: str) -> str:
        """Sanitize description text by stripping redundant Budget, Timeline, or Compensation headers."""
        if not text:
            return text

        budget_timeline_section_pattern = re.compile(
            r"(?m)^\s*(?:BUDGET|ESTIMATED BUDGET|TIMELINE|ESTIMATED DURATION|DURATION|BUDGET & TIMELINE|BUDGET AND TIMELINE|COMPENSATION|NGÂN SÁCH|THỜI GIAN DỰ KIẾN)\s*$\n.*?(?=\n\s*[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĐ][A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĐ\s]{2,}\s*$|\Z)",
            re.DOTALL | re.IGNORECASE
        )
        cleaned = budget_timeline_section_pattern.sub("", text)

        budget_timeline_line_pattern = re.compile(
            r"(?m)^\s*[-•*]?\s*(?:Estimated budget|Estimated duration|Budget|Duration|Ngân sách|Thời gian|Competitive salary in GigCoins|Lương cạnh tranh|Mức lương).*$\n?",
            re.IGNORECASE
        )
        cleaned = budget_timeline_line_pattern.sub("", cleaned)

        return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
