"""
PURPOSE: Unified facade module for RAG (Retrieval-Augmented Generation) indexing, retrieval, and QA.
IMPORTANCE: Critical — Primary entrypoint for RAG domain services across API routes, ingestion runners, and test suites.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/document_processor.py -> app/services/rag/retriever.py -> app/services/rag/query_engine.py -> app/services/rag/__init__.py
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.rag import AnswerConfig, AnswerResult
from app.services.rag.rag_base import RAGBaseService, RelevanceCheck, Result
from app.services.rag.document_processor import DocumentProcessorService
from app.services.rag.retriever import RetrieverService
from app.services.rag.query_engine import QueryEngineService
from app.services.rag.memory import MemoryManager, get_memory_manager
from app.services.rag.hotword_resolver import HotwordResolver, get_hotword_resolver
from app.services.rag.evaluator import EvidenceEvaluatorService

logger = logging.getLogger(__name__)


class RAGService(RAGBaseService):
    """Facade composing DocumentProcessorService, RetrieverService, and QueryEngineService."""

    def __init__(
        self,
        chroma_client: Optional[ChromaDBClient] = None,
        llm_gateway: Optional[LLMGateway] = None,
    ):
        """Initialize RAGService facade with sub-service delegates."""
        super().__init__(chroma_client=chroma_client, llm_gateway=llm_gateway)
        self.doc_processor = DocumentProcessorService(chroma_client=self.chroma, llm_gateway=self.llm)
        self.retriever = RetrieverService(chroma_client=self.chroma, llm_gateway=self.llm)
        self.query_engine = QueryEngineService(chroma_client=self.chroma, llm_gateway=self.llm)

    async def get_embeddings(
        self,
        texts: List[str],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> List[List[float]]:
        """Delegate vector embedding generation."""
        return await super().get_embeddings(texts, provider=provider, model=model, allow_fallback=allow_fallback)

    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Delegate word count text chunking."""
        return self.doc_processor.chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split_text_recursive(self, text: str, max_chars: int = 1200, overlap: int = 300) -> List[str]:
        """Delegate recursive boundary text splitting."""
        return self.doc_processor.split_text_recursive(text, max_chars=max_chars, overlap=overlap)

    async def process_document_semantic(self, document: Dict[str, Any]) -> List[Result]:
        """Delegate semantic document chunk indexing."""
        return await self.doc_processor.process_document_semantic(document)

    async def add_documents(self, collection_name: str, text: str, metadata: Dict[str, Any]) -> None:
        """Delegate vector DB document ingestion."""
        return await self.query_engine.add_documents(collection_name, text, metadata)

    async def retrieve_context(self, collection_name: str, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """Delegate vector context retrieval."""
        return await self.retriever.retrieve_context(collection_name, query, top_k=top_k)

    async def fetch_context_unranked(self, question: str, collection_name: str, retrieval_k: int = 20) -> List[Result]:
        """Delegate raw unranked context retrieval."""
        return await self.retriever.fetch_context_unranked(question, collection_name, retrieval_k=retrieval_k)

    def merge_chunks(self, chunks1: List[Result], chunks2: List[Result]) -> List[Result]:
        """Delegate chunk deduplication and merging."""
        return self.retriever.merge_chunks(chunks1, chunks2)

    async def rerank(self, question: str, chunks: List[Result], final_k: int = 10) -> List[Result]:
        """Delegate LLM chunk reranking."""
        return await self.retriever.rerank(question, chunks, final_k=final_k)

    async def fetch_context(self, original_question: str, collection_name: str) -> List[Result]:
        """Delegate dual-query context retrieval and reranking."""
        return await self.retriever.fetch_context(original_question, collection_name, query_rewriter=self.query_engine.rewrite_query)

    async def rewrite_query(self, question: str, history: List[Dict[str, str]] = []) -> str:
        """Delegate query rewriting."""
        return await self.query_engine.rewrite_query(question, history=history)

    async def check_relevance(self, question: str, history: List[Dict[str, str]] = []) -> RelevanceCheck:
        """Delegate relevance classification."""
        return await self.query_engine.check_relevance(question, history=history)

    async def answer_question(
        self,
        question: str,
        config: Optional[AnswerConfig] = None,
    ) -> AnswerResult:
        """Delegate unified configuration-driven RAG QA execution."""
        return await self.query_engine.answer_question(question, config=config)

    async def auto_ingest_if_empty(self) -> None:
        """Check if Chroma DB collections exist and contain documents; trigger auto-ingestion if empty."""
        try:
            collections = self.chroma.client.list_collections()
            has_docs = False
            for col in collections:
                col_name = getattr(col, "name", str(col))
                try:
                    collection = self.chroma.client.get_collection(col_name)
                    if collection.count() > 0:
                        has_docs = True
                        break
                except Exception:
                    pass

            if not has_docs:
                logger.info("Chroma DB collections are empty. Auto-ingesting knowledge base documents...")
                from scripts.ingest import main as run_ingest
                await asyncio.to_thread(run_ingest)
            else:
                logger.info("Chroma DB collections verified and contain documents.")
        except Exception as e:
            logger.warning(f"Auto ingest check encountered error: {e}")


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Dependency injection helper returning singleton instance of RAGService."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
