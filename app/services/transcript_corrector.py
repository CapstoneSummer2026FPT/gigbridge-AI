"""Transcript correction orchestration for voice interviews."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.services.phonetic_matcher import PhoneticMatcher
from app.services.typo_matcher import TypoMatcher


@dataclass(frozen=True)
class TranscriptCorrectionResult:
    original_text: str
    corrected_text: str
    changed: bool


class TranscriptCorrector:
    """Runs deterministic local transcript correction."""

    def __init__(
        self,
        phonetic_matcher: PhoneticMatcher | None = None,
        typo_matcher: TypoMatcher | None = None,
    ):
        self.phonetic_matcher = phonetic_matcher or PhoneticMatcher()
        self.typo_matcher = typo_matcher or TypoMatcher()

    def correct(
        self,
        transcript: str,
        hotwords: list[str] | None = None,
        phonetic_aliases: Mapping[str, list[str] | str] | None = None,
        language: str | None = None,
    ) -> TranscriptCorrectionResult:
        del language  # Reserved for future language-specific policy.

        original = transcript or ""
        after_phonetic = self.phonetic_matcher.correct(
            original,
            hotwords,
            aliases_by_term=phonetic_aliases,
        )
        after_typo = self.typo_matcher.correct(after_phonetic, hotwords)
        corrected = " ".join(after_typo.split())

        return TranscriptCorrectionResult(
            original_text=original,
            corrected_text=corrected,
            changed=corrected != " ".join(original.split()),
        )
