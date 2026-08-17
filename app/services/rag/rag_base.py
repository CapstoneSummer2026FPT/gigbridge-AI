"""
PURPOSE: Base class and embedding provider dispatch for custom RAG pipelines (OpenAI, Gemini, Ollama).
IMPORTANCE: Critical — Primary embedding generation layer driving vector storage, retrieval, and similarity indexing.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/document_processor.py -> app/services/rag/retriever.py -> app/services/rag/query_engine.py
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import httpx

from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.core.config import settings
from app.core.exceptions import RAGException

logger = logging.getLogger("ai_server.rag_base")


# ── Pydantic Data Models for RAG Pipeline ──────────────────────

class Result(BaseModel):
    """Retrieved knowledge document chunk with metadata."""
    page_content: str
    metadata: Dict[str, Any]


class Chunk(BaseModel):
    """Semantic chunk model with headline, summary, and original text."""
    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query"
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document: Dict[str, Any]) -> Result:
        """Convert Chunk into a Result model with document source metadata."""
        metadata = {"source": document.get("source", ""), "type": document.get("type", "")}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )


class Chunks(BaseModel):
    """Container for multiple semantic Chunk objects."""
    chunks: List[Chunk]


class ChunkMetadata(BaseModel):
    """Metadata container for LLM-generated chunk headline and summary."""
    headline: str = Field(
        description="A brief search-optimized heading for this chunk, typically a few words"
    )
    summary: str = Field(
        description="A 1-2 sentence summary of this chunk's key facts"
    )


class RankOrder(BaseModel):
    """Rank order container for LLM chunk reranking."""
    order: List[int] = Field(
        description="The order of relevance of chunks by chunk id number"
    )


class RelevanceCheck(BaseModel):
    """Relevance check response model."""
    related: bool = Field(description="True if the message is related to GigBridge; False otherwise.")
    topic: str = Field(description="The main topic/subject of the query in the user's language.")
    language: str = Field(description="The language of the user's message: 'vi' or 'en'.")


class RAGBaseService:
    """Base RAG service managing embedding client configurations and vector embedding generation."""

    def __init__(
        self,
        chroma_client: Optional[ChromaDBClient] = None,
        llm_gateway: Optional[LLMGateway] = None,
    ):
        """Initialize RAG base service with Chroma DB client and LLM gateway."""
        self.chroma = chroma_client or get_chroma_client()
        self.llm = llm_gateway or get_llm_gateway()
        self.embedding_model = settings.EMBEDDING_MODEL
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

        if settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        if settings.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        if settings.CLAUDE_API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = settings.CLAUDE_API_KEY

        provider_model_map = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini/gemini-1.5-flash",
            "claude": "anthropic/claude-3-5-sonnet-20240620",
            "local": f"ollama/{settings.LOCAL_MODEL_NAME}"
        }
        default_provider = settings.DEFAULT_LLM_PROVIDER.lower()
        self.qa_model = provider_model_map.get(default_provider, "gpt-4o-mini")
        self.chunk_model = self.qa_model
        self.fallback_model = "gpt-4o-mini" if default_provider != "openai" else "gemini/gemini-1.5-flash"

    async def get_embeddings(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> List[List[float]]:
        """Generate vector embeddings for input text strings using OpenAI, Gemini, or local Ollama.
        
        Flow:
        1. Check for empty input list.
        2. Dispatch to local Ollama HTTP embed API if provider is 'ollama'.
        3. Dispatch to Gemini embeddings API if provider is 'gemini'.
        4. Dispatch to OpenAI embeddings API (or fallback to Gemini if OpenAI key missing).
        """
        selected_provider = (provider or "openai").lower()
        selected_model = model or self.embedding_model

        if not texts:
            return []

        if selected_provider == "ollama":
            return await self._get_ollama_embeddings(texts, selected_model)

        if selected_provider == "gemini":
            return await self._get_gemini_embeddings(texts, selected_model)

        if selected_provider != "openai":
            raise RAGException(f"Unsupported embedding provider: {selected_provider}")

        if not self.openai_client:
            if allow_fallback and provider is None and settings.GEMINI_API_KEY:
                try:
                    return await self._get_gemini_embeddings(texts, "text-embedding-004")
                except Exception as e:
                    logger.error(f"Gemini embeddings fallback failed: {str(e)}")
            raise RAGException("API Key is not configured for generating embeddings.")

        try:
            response = await self.openai_client.embeddings.create(
                model=selected_model,
                input=texts
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            raise RAGException(f"Failed to generate embeddings: {str(e)}")

    async def _get_ollama_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate embeddings via local Ollama HTTP server."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.LOCAL_OLLAMA_URL.rstrip('/')}/api/embed",
                    json={
                        "model": model,
                        "input": texts,
                        "truncate": True,
                    },
                )
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, dict):
                raise RAGException("Ollama returned an invalid embedding response.")

            embeddings = payload.get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise RAGException("Ollama returned an incomplete embedding batch.")

            vectors: List[List[float]] = []
            for embedding in embeddings:
                if not isinstance(embedding, list) or not embedding:
                    raise RAGException("Ollama returned an invalid embedding vector.")
                vector = [float(value) for value in embedding]
                vectors.append(vector)
            return vectors
        except RAGException:
            raise
        except Exception as exc:
            raise RAGException(f"Ollama embedding request failed: {str(exc)}") from exc

    async def _get_gemini_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate embeddings via Gemini OpenAI-compatible embeddings API."""
        if not settings.GEMINI_API_KEY:
            raise RAGException("Gemini API key is not configured for embeddings.")
        try:
            gemini_emb_client = AsyncOpenAI(
                api_key=settings.GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            response = await gemini_emb_client.embeddings.create(
                model=model,
                input=texts,
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            raise RAGException(f"Failed to generate Gemini embeddings: {str(e)}")
