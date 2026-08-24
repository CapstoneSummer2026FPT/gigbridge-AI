"""
PURPOSE: Same-language technical typo correction using RapidFuzz.
IMPORTANCE: Medium — Corrects minor spelling mistakes in STT transcripts against job hotword vocabulary.
READING FLOW: app/services/matching/typo_matcher.py -> app/services/interviews/transcript_corrector.py
"""

from __future__ import annotations

import re
from rapidfuzz import fuzz, process

_TOKEN_RE = re.compile(r"\b[\w.+#-]{3,}\b", re.UNICODE)


class TypoMatcher:
    """Corrects likely technical term typos against job-specific hotwords."""

    def __init__(self, min_score: int = 92):
        """Initialize TypoMatcher with minimum similarity score threshold."""
        self.min_score = min_score

    def correct(self, transcript: str, hotwords: list[str] | None = None) -> str:
        """Correct misspelled technical terms in transcript using RapidFuzz fuzzy matching.
        
        Flow:
        1. Return early if transcript or hotwords list is empty.
        2. Extract candidate hotword terms.
        3. Iterate through transcript tokens via regex replacement callback.
        4. Match fuzzy similarity score against min_score threshold.
        """
        if not transcript or not hotwords:
            return transcript

        candidates = self._candidate_terms(hotwords)
        if not candidates:
            return transcript

        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            if token.casefold() in {candidate.casefold() for candidate in candidates}:
                return token
            if not self._is_technical_candidate(token):
                return token

            best = process.extractOne(token, candidates, scorer=fuzz.WRatio)
            if not best:
                return token

            replacement, score, _ = best
            if score < self.min_score:
                return token
            if abs(len(replacement) - len(token)) > max(2, len(replacement) // 3):
                return token
            return replacement

        return _TOKEN_RE.sub(replace, transcript)

    @staticmethod
    def _candidate_terms(hotwords: list[str]) -> list[str]:
        """Extract unique candidate terms from hotwords list."""
        terms: list[str] = []
        seen = set()
        for hotword in hotwords:
            for part in re.split(r"\s+", str(hotword).strip()):
                cleaned = part.strip(".,;:()[]{}<>\"'")
                if len(cleaned) < 3:
                    continue
                key = cleaned.casefold()
                if key not in seen:
                    terms.append(cleaned)
                    seen.add(key)
        return terms

    @staticmethod
    def _is_technical_candidate(token: str) -> bool:
        """Check if token possesses technical formatting traits (capitalization, special chars)."""
        return (
            any(char.isupper() for char in token[1:])
            or any(char in token for char in ".+#-")
            or token.isalpha()
        )
