"""
PURPOSE: Job-scoped dynamic phonetic transcript correction for technical term STT errors.
IMPORTANCE: High — Enhances transcript accuracy by mapping misrecognized audio phrases to job hotwords.
READING FLOW: app/services/matching/phonetic_matcher.py -> app/services/interviews/transcript_corrector.py
"""

from __future__ import annotations

import re
from collections.abc import Mapping


class PhoneticMatcher:
    """Applies phonetic aliases generated for the current job only."""

    def __init__(self, aliases_by_term: Mapping[str, list[str] | str] | None = None):
        """Initialize PhoneticMatcher with an optional normalized term alias registry."""
        self.aliases_by_term = self._normalize_registry(aliases_by_term or {})

    def correct(
        self,
        transcript: str,
        hotwords: list[str] | None = None,
        aliases_by_term: Mapping[str, list[str] | str] | None = None,
    ) -> str:
        """Correct noisy transcript terms against job hotwords and phonetic aliases.
        
        Flow:
        1. Check for empty transcript.
        2. Merge class registry with call-scoped alias overrides.
        3. Build active alias mappings matching target hotwords.
        4. Apply regex replacements ordered by phrase length.
        """
        if not transcript:
            return transcript

        merged_aliases = dict(self.aliases_by_term)
        merged_aliases.update(self._normalize_registry(aliases_by_term or {}))
        active_aliases = self._active_aliases(hotwords or [], merged_aliases)
        if not active_aliases:
            return transcript

        corrected = transcript
        for noisy_phrase, canonical in sorted(
            active_aliases.items(), key=lambda item: len(item[0]), reverse=True
        ):
            pattern = re.compile(rf"(?<!\w){re.escape(noisy_phrase)}(?!\w)", re.IGNORECASE)
            corrected = pattern.sub(canonical, corrected)

        return corrected

    def _active_aliases(
        self,
        hotwords: list[str],
        aliases_by_term: Mapping[str, list[str] | str],
    ) -> dict[str, str]:
        """Build dictionary of active noisy phrase to canonical term replacements."""
        allowed = self._allowed_terms(hotwords)
        if not allowed:
            return {}

        active: dict[str, str] = {}

        explicit_aliases = self._normalize_registry(aliases_by_term)
        explicit_alias_keys = {
            alias.casefold()
            for aliases in explicit_aliases.values()
            for alias in aliases
        }

        for canonical in hotwords:
            canonical_text = str(canonical).strip()
            if not canonical_text:
                continue
            for alias, alias_target in self._generated_alias_targets(canonical_text).items():
                alias_key = alias.casefold()
                if alias_key in explicit_alias_keys:
                    continue
                if alias_key != alias_target.casefold():
                    active[alias_key] = alias_target

        for canonical, aliases in explicit_aliases.items():
            if canonical.casefold() not in allowed:
                continue
            for alias in aliases:
                active[alias.casefold()] = canonical

        return active

    @staticmethod
    def _generated_alias_targets(term: str) -> dict[str, str]:
        """Generate phonetic alias targets for a technical term."""
        normalized = PhoneticMatcher._normalize_text(term)
        if not normalized:
            return {}

        tokens = [token for token in re.split(r"[\s._+-]+", normalized) if token]
        if len(tokens) <= 1:
            return {alias: term for alias in PhoneticMatcher._generate_aliases(term)}

        targets: dict[str, str] = {
            normalized: term,
            normalized.replace(" ", ""): term,
        }
        for token in tokens:
            for alias in PhoneticMatcher._token_aliases(token):
                if len(alias.strip()) >= 3:
                    targets[alias.strip()] = token
        return targets

    @staticmethod
    def _generate_aliases(term: str) -> set[str]:
        """Generate conservative aliases from a job hotword."""
        normalized = PhoneticMatcher._normalize_text(term)
        if not normalized:
            return set()

        aliases = {
            normalized,
            normalized.replace(" ", ""),
            normalized.replace(".", " "),
            normalized.replace("-", " "),
        }

        tokens = [token for token in re.split(r"[\s._+-]+", normalized) if token]
        if len(tokens) > 1:
            aliases.add(" ".join(tokens))

        for token in tokens or [normalized]:
            aliases.update(PhoneticMatcher._token_aliases(token))

        return {alias.strip() for alias in aliases if len(alias.strip()) >= 3}

    @staticmethod
    def _token_aliases(token: str) -> set[str]:
        """Generate token-level phonetic variants."""
        aliases = {token}

        if token.startswith("f"):
            aliases.add("ph" + token[1:])
        if token.startswith("r"):
            aliases.add("ri " + token[1:])
        if token.startswith("k"):
            aliases.add("c" + token[1:])

        aliases.update(PhoneticMatcher._split_token(token))

        expanded = set(aliases)
        for alias in aliases:
            expanded.add(alias.replace("ck", "c"))
            expanded.add(alias.replace("c", "k"))
            expanded.add(alias.replace("d", "đ"))
            expanded.add(alias.replace("end", "en"))
            expanded.add(alias.replace("end", "enh"))
            expanded.add(alias.replace("end", "kenh"))
            expanded.add(alias.replace("act", "ac"))
            expanded.add(alias.replace("ig", "ich"))

        return expanded

    @staticmethod
    def _split_token(token: str) -> set[str]:
        """Split compound tech tokens into constituent words."""
        aliases: set[str] = set()
        for suffix in ("end", "app", "api", "js", "sql"):
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                aliases.add(token[: -len(suffix)] + " " + suffix)
        if len(token) >= 5:
            middle = len(token) // 2
            aliases.add(token[:middle] + " " + token[middle:])
        return aliases

    @staticmethod
    def _allowed_terms(hotwords: list[str]) -> set[str]:
        """Extract set of allowed lowercase hotwords and word parts."""
        allowed: set[str] = set()
        for hotword in hotwords:
            text = str(hotword).strip()
            if not text:
                continue
            allowed.add(text.casefold())
            for part in re.split(r"\s+", text):
                cleaned = part.strip(".,;:()[]{}<>\"'")
                if cleaned:
                    allowed.add(cleaned.casefold())
        return allowed

    @staticmethod
    def _normalize_text(value: str) -> str:
        """Normalize text by converting camelCase, lowercasing, and replacing special characters."""
        value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
        value = value.casefold()
        value = value.replace("#", " sharp")
        value = value.replace("&", " and ")
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _normalize_registry(
        registry: Mapping[str, list[str] | str]
    ) -> dict[str, list[str]]:
        """Normalize registry mapping of canonical terms to list of aliases."""
        normalized: dict[str, list[str]] = {}
        for canonical_or_alias, aliases_or_canonical in registry.items():
            if isinstance(aliases_or_canonical, str):
                canonical = aliases_or_canonical
                aliases = [canonical_or_alias]
            else:
                canonical = canonical_or_alias
                aliases = aliases_or_canonical

            canonical_text = str(canonical).strip()
            clean_aliases = [
                str(alias).strip()
                for alias in aliases
                if str(alias).strip()
            ]
            if canonical_text and clean_aliases:
                normalized[canonical_text] = clean_aliases
        return normalized
