"""
PURPOSE: Shared algorithms, tokenization, TF-IDF weighting, and Chroma vector retrieval base for candidate & job matching.
IMPORTANCE: Critical — Core mathematical foundation for hybrid vector-semantic and deterministic feature matching.
READING FLOW: app/schemas/matching.py -> app/services/matching/matching_base.py -> app/services/matching/job_matching.py -> app/services/matching/freelancer_matching.py
"""

import asyncio
import hashlib
import logging
import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Set

from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.core.config import settings
from app.core.exceptions import RAGException
from app.services.rag import RAGService, get_rag_service

logger = logging.getLogger("ai_server.matching_base")

_TOKEN_PATTERN = re.compile(r"[a-z0-9+#.]{2,}")
_STOP_WORDS = {
    "and", "are", "for", "from", "into", "that", "the", "this", "with",
    "will", "your", "you", "our", "job", "work", "role", "using", "have",
    "has", "build", "developer", "engineer",
}


class MatchingBaseService:
    """Base matching service providing vector store operations and token relevance algorithms."""

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
    ):
        """Initialize base matching service with RAG service and Chroma DB client."""
        self.rag = rag_service or get_rag_service()
        self.chroma = chroma_client or get_chroma_client()

    @staticmethod
    def hash_text(text: str) -> str:
        """Compute SHA256 hex digest for document change detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def stable_freelancer_id(candidate_id: str) -> str:
        """Generate stable Chroma document ID for freelancer profiles."""
        return f"freelancer:{candidate_id}"

    @staticmethod
    def stable_job_id(job_id: str) -> str:
        """Generate stable Chroma document ID for job requirement profiles."""
        return f"job:{job_id}"

    @staticmethod
    def collection_name_talent() -> str:
        """Compute collection name for freelancer talent profiles based on embedding model."""
        version = re.sub(
            r"[^a-z0-9]+",
            "_",
            (
                f"{settings.MATCHING_EMBEDDING_PROVIDER}_"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ).casefold(),
        ).strip("_")
        return f"freelancers_v1_{version}"[:63]

    @staticmethod
    def collection_name_jobs() -> str:
        """Compute collection name for job posts based on embedding model."""
        version = re.sub(
            r"[^a-z0-9]+",
            "_",
            (
                f"{settings.MATCHING_EMBEDDING_PROVIDER}_"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ).casefold(),
        ).strip("_")
        return f"job_posts_v1_{version}"[:63]

    @staticmethod
    def extract_tokens(*values: Optional[str]) -> Set[str]:
        """Extract sanitized lowercase keyword tokens from input string values.
        
        Splits text using _TOKEN_PATTERN and filters out short terms or stop words.
        """
        tokens: Set[str] = set()
        for value in values:
            if not value:
                continue
            for match in _TOKEN_PATTERN.finditer(value.lower()):
                token = match.group()
                if token not in _STOP_WORDS:
                    tokens.add(token)
        return tokens

    @staticmethod
    def extract_phrases(items: Sequence[Optional[str]]) -> Set[str]:
        """Extract canonicalized skill or category phrase strings.
        
        Normalizes multi-word phrases by trimming whitespace and lowercasing.
        """
        phrases: Set[str] = set()
        for item in items:
            if not item:
                continue
            cleaned = item.strip().lower()
            if cleaned:
                phrases.add(cleaned)
        return phrases

    @staticmethod
    def compute_idf(documents: Iterable[Set[str]]) -> Dict[str, float]:
        """Calculate Inverse Document Frequency (IDF) weights across document tokens.
        
        Uses smooth log weighting formula: log((N + 1) / (df + 1)) + 1.0.
        """
        document_list = list(documents)
        count = len(document_list)
        frequencies: Counter[str] = Counter(
            token for document in document_list for token in document
        )
        return {
            token: math.log((count + 1) / (frequency + 1)) + 1.0
            for token, frequency in frequencies.items()
        }

    @classmethod
    def compute_token_relevance(
        cls,
        query_tokens: Set[str],
        document_tokens: Set[str],
        idf: Dict[str, float],
    ) -> float:
        """Compute weighted token relevance score (0.0 - 100.0) combining IDF coverage and Dice coefficient.
        
        Higher weights are assigned to rare technical terms present in both query and document.
        """
        if not query_tokens or not document_tokens:
            return 0.0
        intersection = query_tokens & document_tokens
        query_weight = sum(idf.get(token, 1.0) for token in query_tokens)
        matched_weight = sum(idf.get(token, 1.0) for token in intersection)
        coverage = matched_weight / query_weight if query_weight else 0.0
        dice = 2.0 * len(intersection) / (len(query_tokens) + len(document_tokens))
        return round(100.0 * (0.8 * coverage + 0.2 * dice), 2)
