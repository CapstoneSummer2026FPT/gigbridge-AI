"""
PURPOSE: Context retrieval, dual-query vector search, chunk deduplication, and LLM-based chunk reranking.
IMPORTANCE: Critical — Core retrieval engine extracting and ordering knowledge base extracts for RAG QA.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/retriever.py -> app/services/rag/query_engine.py
"""

import asyncio
import logging
from typing import Any, Dict, List
from litellm import acompletion

from app.services.rag.rag_base import RAGBaseService, RankOrder, Result
from app.core.exceptions import RAGException

logger = logging.getLogger("ai_server.retriever")


class RetrieverService(RAGBaseService):
    """Handles dual-query retrieval, chunk merging, and LLM reranking."""

    async def fetch_context(self, original_question: str, collection_name: str, query_rewriter=None) -> List[Result]:
        """Execute dual-query retrieval (original query + rewritten query), merge chunks, and rerank.
        
        Flow:
        1. Rewrite user query if query_rewriter callback provided.
        2. Execute parallel vector search for original query and rewritten query.
        3. Merge and deduplicate retrieved chunks.
        4. Re-rank merged chunks via LLM relevance order and return top 10.
        """
        if query_rewriter:
            rewritten_question = await query_rewriter(original_question)
        else:
            rewritten_question = original_question

        logger.info(f"Original query: '{original_question}' | Rewritten query: '{rewritten_question}'")

        chunks1, chunks2 = await asyncio.gather(
            self.fetch_context_unranked(original_question, collection_name, retrieval_k=20),
            self.fetch_context_unranked(rewritten_question, collection_name, retrieval_k=20)
        )

        chunks = self.merge_chunks(chunks1, chunks2)
        reranked = await self.rerank(original_question, chunks, final_k=10)
        return reranked

    async def fetch_context_unranked(
        self, question: str, collection_name: str, retrieval_k: int = 20
    ) -> List[Result]:
        """Embed input question and query Chroma DB collection for raw unranked vector matches."""
        try:
            query_vector = (await self.get_embeddings([question]))[0]
            results = await asyncio.to_thread(
                self.chroma.query_documents,
                collection_name=collection_name,
                query_embeddings=[query_vector],
                n_results=retrieval_k
            )

            chunks = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    chunks.append(Result(
                        page_content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                    ))
            return chunks
        except Exception as e:
            logger.error(f"Unranked context fetch failed: {str(e)}")
            return []

    async def retrieve_context(
        self, collection_name: str, query: str, top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """Fallback simple vector search returning dictionary format."""
        try:
            query_vector = (await self.get_embeddings([query]))[0]
            results = await asyncio.to_thread(
                self.chroma.query_documents,
                collection_name=collection_name,
                query_embeddings=[query_vector],
                n_results=top_k
            )

            docs = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    docs.append({
                        "id": results["ids"][0][i],
                        "page_content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
            return docs
        except Exception as e:
            raise RAGException(f"Context retrieval failed: {str(e)}")

    @staticmethod
    def merge_chunks(chunks1: List[Result], chunks2: List[Result]) -> List[Result]:
        """Deduplicate and merge two lists of Result objects based on page_content."""
        merged = chunks1[:]
        existing = {chunk.page_content for chunk in chunks1}
        for chunk in chunks2:
            if chunk.page_content not in existing:
                merged.append(chunk)
                existing.add(chunk.page_content)
        return merged

    async def rerank(self, question: str, chunks: List[Result], final_k: int = 10) -> List[Result]:
        """Re-rank retrieved chunks by semantic relevance using LLM zero-shot rank order.
        
        Flow:
        1. Return early if chunks list is empty.
        2. Format chunk items into structured ranker prompt.
        3. Invoke LLM to return RankOrder schema.
        4. Reorder chunks by returned ID order and return top final_k.
        """
        if not chunks:
            return []

        system_prompt = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
"""
        user_prompt = f"The user has asked the following question:\n\n{question}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
        user_prompt += "Here are the chunks:\n\n"
        for index, chunk in enumerate(chunks):
            user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
        user_prompt += "Reply only with the list of ranked chunk ids, nothing else."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await acompletion(model=self.qa_model, messages=messages, response_format=RankOrder)
            reply = response.choices[0].message.content
            order = RankOrder.model_validate_json(reply).order
            ranked = []
            for i in order:
                idx = i - 1
                if 0 <= idx < len(chunks):
                    ranked.append(chunks[idx])
            for chunk in chunks:
                if chunk not in ranked:
                    ranked.append(chunk)
            return ranked[:final_k]
        except Exception as e:
            logger.warning(f"Reranking with {self.qa_model} failed: {str(e)}. Falling back to default list order.")
            try:
                response = await acompletion(model=self.fallback_model, messages=messages, response_format=RankOrder)
                reply = response.choices[0].message.content
                order = RankOrder.model_validate_json(reply).order
                ranked = []
                for i in order:
                    idx = i - 1
                    if 0 <= idx < len(chunks):
                        ranked.append(chunks[idx])
                for chunk in chunks:
                    if chunk not in ranked:
                        ranked.append(chunk)
                return ranked[:final_k]
            except Exception:
                return chunks[:final_k]
