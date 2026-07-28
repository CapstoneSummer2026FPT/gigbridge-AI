"""Layered, job-scoped hotword resolution from existing structured metadata."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.core.config import settings


_TOKEN_RE = re.compile(r"[^\s/,;:()[\]{}<>\"']+")
_EDGE_PUNCTUATION = " \t\r\n,;:()[]{}<>\"'"


class HotwordResolver:
    """Build bounded hotwords without a category map or external model call.

    Terms are ordered from the most explicit job configuration to broader
    structured context:

    1. selected/custom skills and explicit phonetic alias canonicals;
    2. the persisted category and major taxonomy names;
    3. the job title;
    4. distinctive spellings found in predefined interview questions.
    """

    def __init__(self, *, max_terms: int | None = None):
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
        """Compatibility entry point for callers that do not need an instance."""
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
        term = re.sub(r"\s+", " ", str(raw_term)).strip(_EDGE_PUNCTUATION)
        return term.lstrip("!?").rstrip(".!?")
