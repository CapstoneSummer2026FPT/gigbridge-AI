"""Bilingual TTS segment routing.

Routes job-specific English terms to an English voice while keeping the rest of
the text in the detected sentence language. Audio stitching quality is handled
by the later stitching phase; this module only decides segment boundaries.
"""

import re
from dataclasses import dataclass


_VIETNAMESE_MARKS = set(
    "\u0103\u00e2\u0111\u00ea\u00f4\u01a1\u01b0"
    "\u00e1\u00e0\u1ea3\u00e3\u1ea1"
    "\u1ea5\u1ea7\u1ea9\u1eab\u1ead"
    "\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7"
    "\u00e9\u00e8\u1ebb\u1ebd\u1eb9"
    "\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7"
    "\u00ed\u00ec\u1ec9\u0129\u1ecb"
    "\u00f3\u00f2\u1ecf\u00f5\u1ecd"
    "\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9"
    "\u1edb\u1edd\u1edf\u1ee1\u1ee3"
    "\u00fa\u00f9\u1ee7\u0169\u1ee5"
    "\u1ee9\u1eeb\u1eed\u1eef\u1ef1"
    "\u00fd\u1ef3\u1ef7\u1ef9\u1ef5"
)
_ENGLISH_WORDS = {
    "a", "an", "and", "are", "as", "can", "could", "do", "for", "from",
    "have", "how", "in", "is", "of", "on", "or", "that", "the", "this",
    "to", "what", "when", "where", "which", "why", "with", "would", "you",
}
_VIETNAMESE_WORDS = {
    "anh", "ban", "cac", "cho", "co", "cua", "da", "de", "duoc", "hay",
    "khi", "la", "mot", "nao", "noi", "ta", "toi", "trong", "va", "ve",
    "voi",
}
_SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|\n+|$)")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class TTSSegment:
    text: str
    language: str


class TTSSegmentRouter:
    """Split text into voice-language segments for bilingual TTS."""

    def route(
        self,
        text: str,
        base_language: str,
        hotwords: list[str] | None = None,
    ) -> list[TTSSegment]:
        if not text:
            return []

        base = self._normalize_language(base_language)
        english_terms = self._english_hotwords(hotwords or [])
        segments: list[TTSSegment] = []

        for sentence in self._split_sentences(text):
            sentence_language = self._detect_sentence_language(sentence, base)
            segments.extend(
                self._route_sentence(sentence, sentence_language, english_terms)
            )

        return self._merge_adjacent(segments)

    def _route_sentence(
        self,
        sentence: str,
        sentence_language: str,
        english_terms: list[str],
    ) -> list[TTSSegment]:
        if not english_terms:
            return [TTSSegment(sentence, sentence_language)]

        matches = self._find_hotword_matches(sentence, english_terms)
        if not matches:
            return [TTSSegment(sentence, sentence_language)]

        segments: list[TTSSegment] = []
        cursor = 0
        for start, end in matches:
            if start > cursor:
                segments.append(TTSSegment(sentence[cursor:start], sentence_language))
            segments.append(TTSSegment(sentence[start:end], "en"))
            cursor = end
        if cursor < len(sentence):
            segments.append(TTSSegment(sentence[cursor:], sentence_language))
        return segments

    @staticmethod
    def _normalize_language(language: str) -> str:
        value = (language or "vi").lower().replace("_", "-")
        if value.startswith("en"):
            return "en"
        return "vi"

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        matches = [match.group(0) for match in _SENTENCE_RE.finditer(text)]
        return matches or [text]

    def _detect_sentence_language(self, sentence: str, base_language: str) -> str:
        lowered = sentence.casefold()
        if any(mark in lowered for mark in _VIETNAMESE_MARKS):
            return "vi"

        words = [word.casefold() for word in _WORD_RE.findall(sentence)]
        if not words:
            return base_language

        english_hits = sum(1 for word in words if word in _ENGLISH_WORDS)
        vietnamese_hits = sum(1 for word in words if word in _VIETNAMESE_WORDS)

        if english_hits >= 2 and english_hits > vietnamese_hits:
            return "en"
        if vietnamese_hits >= 2 and vietnamese_hits >= english_hits:
            return "vi"
        return base_language

    def _english_hotwords(self, hotwords: list[str]) -> list[str]:
        seen = set()
        terms = []
        for hotword in hotwords:
            term = str(hotword).strip()
            key = term.casefold()
            if not term or key in seen:
                continue
            if self._looks_english_term(term):
                terms.append(term)
                seen.add(key)
        return sorted(terms, key=len, reverse=True)

    def _looks_english_term(self, term: str) -> bool:
        lowered = term.casefold()
        if any(mark in lowered for mark in _VIETNAMESE_MARKS):
            return False
        words = [word.casefold() for word in _WORD_RE.findall(term)]
        if not words:
            return False
        if all(word in _VIETNAMESE_WORDS for word in words):
            return False
        return any(any("a" <= ch.lower() <= "z" for ch in word) for word in words)

    @staticmethod
    def _find_hotword_matches(sentence: str, terms: list[str]) -> list[tuple[int, int]]:
        matches: list[tuple[int, int]] = []
        occupied: list[tuple[int, int]] = []
        for term in terms:
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
            for match in pattern.finditer(sentence):
                span = match.span()
                if any(not (span[1] <= start or span[0] >= end) for start, end in occupied):
                    continue
                matches.append(span)
                occupied.append(span)
        return sorted(matches)

    @staticmethod
    def _merge_adjacent(segments: list[TTSSegment]) -> list[TTSSegment]:
        merged: list[TTSSegment] = []
        for segment in segments:
            if not segment.text:
                continue
            if merged and merged[-1].language == segment.language:
                previous = merged[-1]
                merged[-1] = TTSSegment(previous.text + segment.text, previous.language)
            else:
                merged.append(segment)
        return merged
