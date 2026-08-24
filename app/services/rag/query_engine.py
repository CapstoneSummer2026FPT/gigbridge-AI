"""
PURPOSE: Unified configuration-driven RAG QA query execution, query rewriting, and domain relevance classification.
IMPORTANCE: Critical — Primary orchestrator handling knowledge base questions, structured answers, and fallback checks.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/retriever.py -> app/services/rag/query_engine.py -> app/api/routes/rag.py
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from litellm import acompletion

from app.schemas.rag import AnswerConfig, AnswerResult
from app.services.rag.rag_base import RAGBaseService, RelevanceCheck
from app.services.rag.retriever import RetrieverService
from app.services.rag.document_processor import DocumentProcessorService
from app.core.config import settings
from app.core.exceptions import RAGException

logger = logging.getLogger("ai_server.query_engine")


class QueryEngineService(RAGBaseService):
    """Orchestrates query rewriting, domain relevance checking, document ingestion, and full RAG QA execution."""

    def __init__(self, *args, **kwargs):
        """Initialize QueryEngineService with retriever and document processor delegates."""
        super().__init__(*args, **kwargs)
        self.retriever = RetrieverService(chroma_client=self.chroma, llm_gateway=self.llm)
        self.doc_processor = DocumentProcessorService(chroma_client=self.chroma, llm_gateway=self.llm)

    async def answer_question(
        self,
        question: str,
        config: Optional[AnswerConfig] = None,
    ) -> AnswerResult:
        """Execute unified configuration-driven RAG answering flow.
        
        Flow:
        1. Parse AnswerConfig (defaulting if None).
        2. Perform relevance classification if no structured response format is requested.
           If query is unrelated to GigBridge, return polite non-relevant response directly.
        3. Retrieval Phase: Query single collection or parallel retrieval groups (with optional rewriting/reranking).
        4. Prompt Assembly: Format system and user messages using Jinja templates or defaults.
        5. LLM Completion Phase: Generate text answer or structured Pydantic object.
        6. Measure latency metrics and return AnswerResult.
        """
        start_time = time.perf_counter()

        if config is None:
            config = AnswerConfig()

        if config.response_format is None:
            rel = await self.check_relevance(question, config.history)
            if not rel.related:
                topic = rel.topic or ("this topic" if rel.language == "en" else "chủ đề này")
                if rel.language == "vi":
                    answer = f"Xin lỗi, nhưng tôi không có thông tin nào về {topic}. Tôi chỉ có thể cung cấp thông tin liên quan đến GigBridge. Nếu bạn có câu hỏi nào về GigBridge, hãy cho tôi biết!"
                else:
                    answer = f"Sorry, but I don't have any information about {topic}. I can only provide information related to GigBridge. If you have any questions about GigBridge, please let me know!"

                total_time = (time.perf_counter() - start_time) * 1000.0
                return AnswerResult(
                    answer=answer,
                    sources=[],
                    latency_ms=total_time,
                    retrieval_time_ms=0.0,
                    llm_time_ms=total_time,
                    prompt_tokens=0,
                    completion_tokens=0
                )

        retrieval_start = time.perf_counter()
        chunks = []

        if config.retrieval_groups:
            try:
                if config.style == "precision":
                    rewritten_query = await self.rewrite_query(question)
                    embeddings = await self.get_embeddings([question, rewritten_query])
                    original_vector = embeddings[0]
                    rewritten_vector = embeddings[1]

                    async def query_group_precision(group):
                        results1, results2 = await asyncio.gather(
                            asyncio.to_thread(
                                self.chroma.query_documents,
                                collection_name=config.collection_name,
                                query_embeddings=[original_vector],
                                n_results=max(group.n_results * 2, 20),
                                where=group.where
                            ),
                            asyncio.to_thread(
                                self.chroma.query_documents,
                                collection_name=config.collection_name,
                                query_embeddings=[rewritten_vector],
                                n_results=max(group.n_results * 2, 20),
                                where=group.where
                            )
                        )

                        g1 = []
                        if results1 and "documents" in results1 and results1["documents"]:
                            for i in range(len(results1["documents"][0])):
                                g1.append(self.retriever.Result(
                                    page_content=results1["documents"][0][i],
                                    metadata=results1["metadatas"][0][i] if results1["metadatas"] else {}
                                ))

                        g2 = []
                        if results2 and "documents" in results2 and results2["documents"]:
                            for i in range(len(results2["documents"][0])):
                                g2.append(self.retriever.Result(
                                    page_content=results2["documents"][0][i],
                                    metadata=results2["metadatas"][0][i] if results2["metadatas"] else {}
                                ))

                        merged = self.retriever.merge_chunks(g1, g2)
                        if group.name in ["categories", "skills"] and len(merged) > group.n_results:
                            return await self.retriever.rerank(question, merged, final_k=group.n_results)
                        return merged[:group.n_results]

                    group_results = await asyncio.gather(*(query_group_precision(g) for g in config.retrieval_groups))
                else:
                    prompt_embeddings = await self.get_embeddings([question])
                    query_vector = prompt_embeddings[0]

                    async def query_group_fast(group):
                        results = await asyncio.to_thread(
                            self.chroma.query_documents,
                            collection_name=config.collection_name,
                            query_embeddings=[query_vector],
                            n_results=group.n_results,
                            where=group.where
                        )
                        g = []
                        if results and "documents" in results and results["documents"]:
                            for i in range(len(results["documents"][0])):
                                g.append(self.retriever.Result(
                                    page_content=results["documents"][0][i],
                                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                                ))
                        return g

                    group_results = await asyncio.gather(*(query_group_fast(g) for g in config.retrieval_groups))

                seen_content = set()
                for gr in group_results:
                    for chunk in gr:
                        if chunk.page_content not in seen_content:
                            seen_content.add(chunk.page_content)
                            chunks.append(chunk)
            except Exception as e:
                logger.error(f"Group retrieval failed: {e}")
        else:
            top_k = config.top_k
            if config.style == "fast" and config.top_k == 15:
                top_k = 5

            if config.style == "fast":
                chunks = await self.retriever.fetch_context_unranked(question, config.collection_name, retrieval_k=top_k)
            else:
                chunks = await self.retriever.fetch_context(question, config.collection_name, query_rewriter=self.rewrite_query)

        retrieval_time = (time.perf_counter() - retrieval_start) * 1000.0

        context_str = "\n\n".join(
            f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
        )

        if config.system_prompt:
            system_prompt = config.system_prompt
        else:
            system_prompt = f"""
You are a knowledgeable, friendly assistant representing the company GigBridge.
You are chatting with a user about GigBridge.
Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
If you don't know the answer, say so.
For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{context_str}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""

        if config.user_template:
            from app.prompts.manager import get_prompt_manager
            pm = get_prompt_manager()
            allowed_majors, allowed_categories, available_skills = self._extract_taxonomy_from_chunks(chunks)
            user_content = pm.render_prompt(
                config.user_template,
                {
                    "client_prompt": question,
                    "allowed_majors": allowed_majors,
                    "allowed_categories": allowed_categories,
                    "available_skills": available_skills,
                    "context_str": context_str,
                }
            )
        else:
            user_content = question

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        llm_start = time.perf_counter()
        target_model = config.model or self.qa_model

        try:
            if config.response_format:
                response = await acompletion(
                    model=target_model,
                    messages=messages,
                    response_format=config.response_format,
                    temperature=config.temperature or 0.0
                )
                raw_reply = response.choices[0].message.content
                try:
                    parsed_answer = config.response_format.model_validate_json(raw_reply)
                except Exception:
                    parsed_answer = raw_reply
            else:
                response = await acompletion(
                    model=target_model,
                    messages=messages,
                    temperature=config.temperature or 0.7
                )
                parsed_answer = response.choices[0].message.content

            llm_time = (time.perf_counter() - llm_start) * 1000.0
            total_time = (time.perf_counter() - start_time) * 1000.0

            sources_meta = [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks]

            return AnswerResult(
                answer=parsed_answer,
                sources=sources_meta,
                latency_ms=total_time,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=llm_time,
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) if hasattr(response, "usage") else 0,
                completion_tokens=getattr(response.usage, "completion_tokens", 0) if hasattr(response, "usage") else 0
            )
        except Exception as exc:
            logger.error(f"QA LLM execution failed: {exc}")
            raise RAGException(f"Failed to generate RAG response: {str(exc)}") from exc

    async def rewrite_query(self, question: str, history: List[Dict[str, str]] = []) -> str:
        """Rewrite user query into a short search-optimized query using conversation history."""
        history_str = json.dumps(history) if history else "[]"
        message = f"""
You are in a conversation with a user, answering questions about the company GigBridge.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history_str}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
        messages = [{"role": "system", "content": message}]
        try:
            response = await acompletion(model=self.qa_model, messages=messages)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Query rewrite with {self.qa_model} failed: {str(e)}. Trying fallback {self.fallback_model}.")
            try:
                response = await acompletion(model=self.fallback_model, messages=messages)
                return response.choices[0].message.content.strip()
            except Exception:
                return question

    async def check_relevance(self, question: str, history: List[Dict[str, str]] = []) -> RelevanceCheck:
        """Check if user query is related to GigBridge services or platform features."""
        system_prompt = """You are a classifier for the GigBridge assistant.
Determine if the user's message is a query or statement related to the company GigBridge, its services, features, platform, job posts, talent matching, candidate vetting, or content in the GigBridge knowledge base.
Greeting messages (like "hello", "hi", "xin chào") or questions about what you can do/what is your purpose are considered RELATED.
General knowledge questions, history, coding questions not about GigBridge, arithmetic, or requests about unrelated subjects are UNRELATED.

You must respond ONLY with a JSON object matching this schema:
{
  "related": true/false,
  "topic": "the main topic/subject of the query in the user's language",
  "language": "vi" or "en"
}
"""
        history_str = json.dumps(history) if history else "[]"
        user_prompt = f"Conversation History:\n{history_str}\n\nUser Question:\n{question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await acompletion(model=self.qa_model, messages=messages, response_format=RelevanceCheck)
            reply = response.choices[0].message.content
            return RelevanceCheck.model_validate_json(reply)
        except Exception as e:
            logger.warning(f"Relevance check with {self.qa_model} failed: {e}. Retrying fallback {self.fallback_model}...")
            try:
                response = await acompletion(model=self.fallback_model, messages=messages, response_format=RelevanceCheck)
                reply = response.choices[0].message.content
                return RelevanceCheck.model_validate_json(reply)
            except Exception as e2:
                logger.error(f"Relevance check failed completely: {e2}. Defaulting to related=True.")
                is_vi = any(char in "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ" for char in question)
                return RelevanceCheck(related=True, topic="", language="vi" if is_vi else "en")

    async def add_documents(self, collection_name: str, text: str, metadata: Dict[str, Any]) -> None:
        """Chunk text, generate embeddings, and write chunks to specified Chroma DB collection."""
        chunks = self.doc_processor.chunk_text(text)
        if not chunks:
            return

        embeddings = await self.get_embeddings(chunks)
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [metadata.copy() for _ in chunks]

        try:
            self.chroma.add_documents(
                collection_name=collection_name,
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
        except Exception as e:
            raise RAGException(f"Failed to write documents to vector DB: {str(e)}")

    def _extract_taxonomy_from_chunks(self, chunks: List[Any]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """Extract allowed_majors, allowed_categories, and available_skills from retrieved RAG chunks and full taxonomy cache."""
        from app.services.job_posts.job_post_base import get_full_taxonomy
        taxonomy = get_full_taxonomy()

        allowed_majors = taxonomy["majors"].copy() if taxonomy["majors"] else [
            {"major_id": "dd491f54-221f-4b80-aa10-227f1ea49a12", "name": "Công nghệ thông tin"},
            {"major_id": "cb887a7d-2539-469b-98b7-a4417207242e", "name": "AI, Dữ liệu & Tự động hóa"},
            {"major_id": "f84d17f5-ab06-4773-8863-4da24fa8a502", "name": "Thiết kế & Sáng tạo số"},
            {"major_id": "78cff18c-16fd-4654-8782-f1fbe85c5e89", "name": "Marketing & Growth"},
            {"major_id": "5ceb0a5e-e851-4e07-90f8-edc08410af69", "name": "Nội dung, Viết lách & Dịch thuật"},
            {"major_id": "9e65412d-a7b8-41ef-bebf-611e555cf33a", "name": "Sản phẩm, Quản lý dự án & QA"},
            {"major_id": "31ebb0b3-8d48-42d2-86f3-65edc75b5a11", "name": "Kinh doanh, Vận hành & Hỗ trợ ảo"},
            {"major_id": "9aad2513-e82d-474f-ae10-b56fed4c6353", "name": "Tài chính, Pháp lý & Tư vấn online"},
            {"major_id": "10191a40-2a6b-41b4-a247-ddbbb18d6cff", "name": "Giáo dục trực tuyến & E-learning"},
            {"major_id": "53c6622e-0e40-4e9c-889e-b8fc0ab228fe", "name": "Blockchain, Game & XR"},
        ]

        allowed_categories = taxonomy["categories"].copy()
        available_skills = []
        seen_skills = set()

        for chunk in chunks:
            meta = getattr(chunk, "metadata", {}) or {}
            item_type = meta.get("type", "")
            if item_type == "skill" or "skill_id" in meta:
                s_id = meta.get("skill_id", "")
                name = meta.get("name", "")
                if s_id and s_id not in seen_skills:
                    seen_skills.add(s_id)
                    available_skills.append({"skill_id": s_id, "name": name})

        return allowed_majors, allowed_categories, available_skills
