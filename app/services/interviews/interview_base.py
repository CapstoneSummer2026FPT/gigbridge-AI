"""
PURPOSE: Shared helper utilities and base configuration for interview session lifecycle, STT, TTS, and judgement.
IMPORTANCE: Critical — Core utility layer used across all interview sub-services (language resolution, hotwords, alias cleaning).
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_session.py
"""

import logging
import re
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.rag.hotword_resolver import HotwordResolver, get_hotword_resolver
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.audio.voice import VoiceService, get_voice_service

logger = logging.getLogger("ai_server.interview_base")

VIETNAMESE_DIACRITICS = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
VIETNAMESE_WORDS = {
    "va", "hoac", "cho", "voi", "cac", "nhung", "ung", "vien",
    "cong", "viec", "du", "an", "kinh", "nghiem", "ky", "nang",
    "lap", "trinh", "thiet", "ke", "phat", "trien", "yeu", "cau",
}


class InterviewBaseService:
    """Base class providing shared dependencies, language detection, and hotword construction helpers."""

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        voice_service: Optional[VoiceService] = None,
        hotword_resolver: Optional[HotwordResolver] = None,
    ):
        """Initialize base interview service with LLM gateway, voice service, and hotword resolver."""
        self.llm = llm_gateway or get_llm_gateway()
        self.voice = voice_service or get_voice_service()
        self.hotword_resolver = hotword_resolver or get_hotword_resolver()
        self.max_questions = settings.MAX_INTERVIEW_QUESTIONS

    @classmethod
    def resolve_interview_language(
        cls,
        requested_language: Optional[str],
        job_title: str,
        job_description: str,
    ) -> str:
        """Resolve requested interview language string or infer from job post text."""
        requested = (requested_language or "auto").strip().lower().replace("_", "-")
        if requested in {"vi", "vi-vn", "vietnamese"}:
            return "vi"
        if requested in {"en", "en-us", "en-gb", "english"}:
            return "en"
        return cls.infer_job_language(job_title, job_description)

    @staticmethod
    def infer_job_language(job_title: str, job_description: str) -> str:
        """Infer whether a job post is in Vietnamese or English using diacritics and vocabulary hits."""
        text = f"{job_title} {job_description}".lower()
        if not text.strip():
            return "vi"

        if any(char in text for char in VIETNAMESE_DIACRITICS):
            return "vi"

        tokens = set(re.findall(r"[a-zA-Z]+", text))
        vietnamese_hits = len(tokens & VIETNAMESE_WORDS)
        return "vi" if vietnamese_hits >= 3 else "en"

    @staticmethod
    def language_name(language: str) -> str:
        """Return display language name ('Vietnamese' or 'English')."""
        return "Vietnamese" if (language or "").lower().startswith("vi") else "English"

    @staticmethod
    def clean_terms(terms: List[str]) -> List[str]:
        """Deduplicate and clean list of terms preserving order."""
        seen = set()
        cleaned = []
        for term in terms or []:
            value = str(term).strip()
            key = value.casefold()
            if value and key not in seen:
                cleaned.append(value)
                seen.add(key)
        return cleaned

    @staticmethod
    def clean_aliases(aliases: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Deduplicate and clean phonetic alias dictionary."""
        cleaned: Dict[str, List[str]] = {}
        for canonical, values in (aliases or {}).items():
            canonical_text = str(canonical).strip()
            if not canonical_text:
                continue
            alias_values = []
            seen = set()
            for value in values or []:
                alias = str(value).strip()
                key = alias.casefold()
                if alias and key not in seen:
                    alias_values.append(alias)
                    seen.add(key)
            if alias_values:
                cleaned[canonical_text] = alias_values
        return cleaned

    @classmethod
    def build_hotwords(
        cls,
        job_title: str,
        job_skills: List[str],
        job_description: Optional[str] = None,
        job_major: Optional[str] = None,
        job_category: Optional[str] = None,
        job_questions: Optional[List[str]] = None,
        phonetic_aliases: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """Build reliable hotwords set for voice recognition."""
        return HotwordResolver.build_reliable_terms(
            job_title,
            job_skills,
            job_major=job_major,
            job_category=job_category,
            job_questions=job_questions,
            phonetic_aliases=phonetic_aliases,
            max_terms=settings.HOTWORD_MAX_TERMS,
        )

    _build_hotwords = build_hotwords
