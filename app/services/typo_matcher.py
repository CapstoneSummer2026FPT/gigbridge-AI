"""Same-language technical typo correction using RapidFuzz."""

from __future__ import annotations

import re

from rapidfuzz import fuzz, process


_TOKEN_RE = re.compile(r"\b[\w.+#-]{3,}\b", re.UNICODE)


class TypoMatcher:
    """Corrects likely typos against job-specific hotwords."""

    def __init__(self, min_score: int = 92):
        self.min_score = min_score

    def correct(self, transcript: str, hotwords: list[str] | None = None) -> str:
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
        return (
            any(char.isupper() for char in token[1:])
            or any(char in token for char in ".+#-")
            or token.isalpha()
        )
