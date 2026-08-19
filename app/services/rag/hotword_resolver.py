"""
PURPOSE: Layered, job-scoped hotword resolution from structured metadata (skills, taxonomy, title, interview questions).
IMPORTANCE: High — Provides vocabulary hotwords to voice STT engines for high recognition accuracy.
READING FLOW: app/services/rag/hotword_resolver.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_session.py
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.core.config import settings

_TOKEN_RE = re.compile(r"[^\s/,;:()[\]{}<>\"']+")
_EDGE_PUNCTUATION = " \t\r\n,;:()[]{}<>\"'"


class HotwordResolver:
    """Builds bounded hotword vocabulary list without external model calls."""

    def __init__(self, *, max_terms: int | None = None):
        """Initialize HotwordResolver with max terms limit."""
        self.max_terms = max_terms or settings.HOTWORD_MAX_TERMS

    def resolve(
        self,
        job_title: str,
        job_skills: Sequence[str] | None = None,
        *,
        job_major: str | None = None,
        job_category: str | None = None,
        job_questions: Sequence[str] | None = None,
        phonetic_aliases: Mapping[str, Sequence[str] | str] | None = None,
    ) -> list[str]:
        """Resolve hotword terms list ordered by relevance priority.
        
        Priority:
        1. Selected/custom skills & explicit phonetic alias canonicals.
        2. Category and major taxonomy names.
        3. Job title.
        4. Distinctive technical spellings in predefined interview questions.
        """
        alias_canonicals = list((phonetic_aliases or {}).keys())
        taxonomy = [job_category or "", job_major or ""]
        question_terms = self._distinctive_terms(job_questions or [])

        return self._clean_terms(
            [
                *(job_skills or []),
                *alias_canonicals,
                *taxonomy,
                job_title,
                *question_terms,
            ],
            max_terms=self.max_terms,
        )

    @classmethod
    def build_reliable_terms(
        cls,
        job_title: str,
        job_skills: Sequence[str] | None = None,
        *,
        job_major: str | None = None,
        job_category: str | None = None,
        job_questions: Sequence[str] | None = None,
        phonetic_aliases: Mapping[str, Sequence[str] | str] | None = None,
        max_terms: int = 50,
    ) -> list[str]:
        """Class method entrypoint for hotword construction."""
        return cls(max_terms=max_terms).resolve(
            job_title,
            job_skills,
            job_major=job_major,
            job_category=job_category,
            job_questions=job_questions,
            phonetic_aliases=phonetic_aliases,
        )

    @classmethod
    def _distinctive_terms(cls, values: Sequence[str]) -> list[str]:
        """Extract camelCase and technical terms from question strings."""
        terms: list[str] = []
        for value in values:
            for raw_token in _TOKEN_RE.findall(str(value)):
                token = cls._normalize_term(raw_token)
                if not token or not any(char.isalpha() for char in token):
                    continue
                has_lower = any(char.islower() for char in token)
                is_camel_case = has_lower and any(
                    char.isupper() for char in token[1:]
                )
                has_technical_symbol = has_lower and any(
                    char in token for char in ("#", ".", "+")
                )
                if is_camel_case or has_technical_symbol:
                    terms.append(token)
        return terms

    @classmethod
    def _clean_terms(
        cls,
        terms: Sequence[object],
        *,
        max_terms: int,
    ) -> list[str]:
        """Sanitize and deduplicate hotword terms list."""
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw_term in terms:
            term = cls._normalize_term(raw_term)
            key = term.casefold()
            if (
                not term
                or key in seen
                or len(term) > 80
                or len(term.split()) > 6
                or not any(char.isalpha() for char in term)
            ):
                continue
            cleaned.append(term)
            seen.add(key)
            if len(cleaned) >= max_terms:
                break
        return cleaned

    @staticmethod
    def _normalize_term(raw_term: object) -> str:
        """Strip surrounding punctuation and whitespace."""
        term = re.sub(r"\s+", " ", str(raw_term)).strip(_EDGE_PUNCTUATION)
        return term.lstrip("!?").rstrip(".!?")


_hotword_resolver = HotwordResolver()


def get_hotword_resolver() -> HotwordResolver:
    """Dependency injection helper returning singleton instance of HotwordResolver."""
    return _hotword_resolver
