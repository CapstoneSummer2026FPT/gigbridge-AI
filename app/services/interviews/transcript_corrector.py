"""
PURPOSE: Transcript correction orchestration combining phonetic alias and RapidFuzz typo matchers.
IMPORTANCE: High — Ensures STT transcripts of technical terms are accurately corrected before answer confirmation.
READING FLOW: app/services/matching/phonetic_matcher.py -> app/services/matching/typo_matcher.py -> app/services/interviews/transcript_corrector.py -> app/services/interviews/interview_stt.py
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.services.matching.phonetic_matcher import PhoneticMatcher
from app.services.matching.typo_matcher import TypoMatcher


@dataclass(frozen=True)
class TranscriptCorrectionResult:
    """Result data container for transcript correction."""
    original_text: str
    corrected_text: str
    changed: bool


class TranscriptCorrector:
    """Runs deterministic local transcript correction pipeline."""

    def __init__(
        self,
        phonetic_matcher: PhoneticMatcher | None = None,
        typo_matcher: TypoMatcher | None = None,
    ):
        """Initialize TranscriptCorrector with phonetic and typo matchers."""
        self.phonetic_matcher = phonetic_matcher or PhoneticMatcher()
        self.typo_matcher = typo_matcher or TypoMatcher()

    def correct(
        self,
        transcript: str,
        hotwords: list[str] | None = None,
        phonetic_aliases: Mapping[str, list[str] | str] | None = None,
        language: str | None = None,
    ) -> TranscriptCorrectionResult:
        """Run transcript correction through phonetic alias matcher then typo matcher.
        
        Flow:
        1. Capture original transcript text.
        2. Apply phonetic matcher using job hotwords and aliases.
        3. Apply RapidFuzz typo matcher.
        4. Normalize whitespace and return TranscriptCorrectionResult.
        """
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
