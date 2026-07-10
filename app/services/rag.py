import uuid
import logging
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential
import litellm
from litellm import acompletion, completion

from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.core.config import settings
from app.core.exceptions import RAGException

logger = logging.getLogger("ai_server.rag_service")

# Pydantic models for semantic RAG pipelines
class Result(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

class Chunk(BaseModel):
    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document: Dict[str, Any]) -> Result:
        metadata = {"source": document.get("source", ""), "type": document.get("type", "")}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )

class Chunks(BaseModel):
    chunks: List[Chunk]

class RankOrder(BaseModel):
    order: List[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )

class RAGService:
    """Service coordinates custom RAG pipelines (indexing, embeddings, retrieval, and reranking)"""
    
    def __init__(
        self,
        chroma_client: ChromaDBClient = get_chroma_client(),
        llm_gateway: LLMGateway = get_llm_gateway()
    ):
        self.chroma = chroma_client
        self.llm = llm_gateway
        self.embedding_model = settings.EMBEDDING_MODEL
        # Initialize AsyncOpenAI only for embeddings
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
        # Setup API Keys for litellm
        if settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        if settings.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        if settings.CLAUDE_API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = settings.CLAUDE_API_KEY

        # Set default models
        self.chunk_model = "openai/gpt-4.1-nano"
        self.qa_model = "groq/openai/gpt-oss-120b"
        self.fallback_model = "gpt-4o-mini"

    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Splits text into overlapping chunks using standard word counting.
        """
        words = text.split()
        chunks = []
        stride = chunk_size - chunk_overlap
        if stride <= 0:
            stride = chunk_size // 2
            
        for i in range(0, len(words), stride):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
        return chunks

    def make_chunk_prompt(self, document: Dict[str, Any], average_chunk_size: int = 100) -> str:
        how_many = (len(document["text"]) // average_chunk_size) + 1
        return f"""
You take a document and you split the document into overlapping chunks for a KnowledgeBase.

The document is from the shared drive of a company called GigBridge.
The document is of type: {document["type"]}
The document has been retrieved from: {document["source"]}

A chatbot will use these chunks to answer questions about the company.
You should divide up the document as you see fit, being sure that the entire document is returned across the chunks - don't leave anything out.
This document should probably be split into at least {how_many} chunks, but you can have more or less as appropriate, ensuring that there are individual chunks to answer specific questions.
There should be overlap between the chunks as appropriate; typically about 25% overlap or about 50 words, so you have the same text in multiple chunks for best retrieval results.

For each chunk, you should provide a headline, a summary, and the original text of the chunk.
Together your chunks should represent the entire document with overlap.

Here is the document:

{document["text"]}

Respond with the chunks.
"""

    async def process_document_semantic(self, document: Dict[str, Any]) -> List[Result]:
        """
        Splits a document semantically using LLM structure generation.
        """
        if document.get("is_pre_chunked"):
            return [chunk.as_result(document) for chunk in document["chunks"]]

        prompt = self.make_chunk_prompt(document)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Use acompletion for async LLM call
            response = await acompletion(
                model=self.chunk_model,
                messages=messages,
                response_format=Chunks
            )
            reply = response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Semantic chunking with {self.chunk_model} failed: {str(e)}. Retrying with {self.fallback_model}.")
            try:
                response = await acompletion(
                    model=self.fallback_model,
                    messages=messages,
                    response_format=Chunks
                )
                reply = response.choices[0].message.content
            except Exception as e2:
                logger.error(f"Semantic chunking failed completely: {str(e2)}")
                # Sequentially fallback to standard word-based chunker
                chunks = self.chunk_text(document["text"])
                return [
                    Result(
                        page_content=f"Section from {document['source']}\n\n{chunk}",
                        metadata={"source": document["source"], "type": document["type"]}
                    ) for chunk in chunks
                ]

        try:
            doc_as_chunks = Chunks.model_validate_json(reply).chunks
            return [chunk.as_result(document) for chunk in doc_as_chunks]
        except Exception as parse_err:
            logger.error(f"Failed to parse semantic chunks JSON: {str(parse_err)}")
            # Fallback to standard word-based chunker
            chunks = self.chunk_text(document["text"])
            return [
                Result(
                    page_content=f"Section from {document['source']}\n\n{chunk}",
                    metadata={"source": document["source"], "type": document["type"]}
                ) for chunk in chunks
            ]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for input texts using OpenAI client or Gemini endpoint.
        """
        if not self.openai_client:
            # Check if Gemini key is set, try to use it as OpenAI compatible endpoint
            if settings.GEMINI_API_KEY:
                try:
                    gemini_emb_client = AsyncOpenAI(
                        api_key=settings.GEMINI_API_KEY,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                    )
                    model = "text-embedding-004" if self.embedding_model == "text-embedding-3-large" else self.embedding_model
                    response = await gemini_emb_client.embeddings.create(
                        model=model,
                        input=texts
                    )
                    return [e.embedding for e in response.data]
                except Exception as e:
                    logger.error(f"Gemini embeddings failed: {str(e)}")
            raise RAGException("API Key is not configured for generating embeddings.")
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            raise RAGException(f"Failed to generate embeddings: {str(e)}")

    async def add_documents(self, collection_name: str, text: str, metadata: Dict[str, Any]) -> None:
        """
        Chunks text, embeds it, and writes chunks to Chroma DB collection.
        Used for programmatic document updates.
        """
        chunks = self.chunk_text(text)
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

    async def retrieve_context(self, collection_name: str, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """
        Fallback implementation for simple non-pipeline database queries.
        """
        try:
            query_vector = (await self.get_embeddings([query]))[0]
            results = self.chroma.query_documents(
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

    async def rewrite_query(self, question: str, history: List[Dict[str, str]] = []) -> str:
        """
        Rewrites user query to be optimized for database retrieval using conversation history.
        """
        history_str = json.dumps(history) if history else "[]"
        message = f"""
You are in a conversation with a user, answering questions about the company GigBridge.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history_str}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
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

    async def rerank(self, question: str, chunks: List[Result], final_k: int = 10) -> List[Result]:
        """
        Rerank retrieved chunks by relevance using LLM ranking order.
        """
        if not chunks:
            return []
            
        system_prompt = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
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

    async def fetch_context_unranked(self, question: str, collection_name: str, retrieval_k: int = 20) -> List[Result]:
        """
        Embeds the query and queries the Chroma DB collection.
        """
        try:
            query_vector = (await self.get_embeddings([question]))[0]
            results = self.chroma.query_documents(
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

    def merge_chunks(self, chunks1: List[Result], chunks2: List[Result]) -> List[Result]:
        merged = chunks1[:]
        existing = [chunk.page_content for chunk in chunks1]
        for chunk in chunks2:
            if chunk.page_content not in existing:
                merged.append(chunk)
        return merged

    async def fetch_context(self, original_question: str, collection_name: str) -> List[Result]:
        """
        Implements dual-query retrieval (original query + rewritten query), merging, and reranking.
        """
        rewritten_question = await self.rewrite_query(original_question)
        logger.info(f"Original query: '{original_question}' | Rewritten query: '{rewritten_question}'")
        
        chunks1 = await self.fetch_context_unranked(original_question, collection_name, retrieval_k=20)
        chunks2 = await self.fetch_context_unranked(rewritten_question, collection_name, retrieval_k=20)
        
        chunks = self.merge_chunks(chunks1, chunks2)
        reranked = await self.rerank(original_question, chunks, final_k=10)
        return reranked

    async def answer_question(
        self,
        question: str,
        config: Optional[Any] = None,
    ) -> Any:
        """
        Unified configuration-driven RAG answering flow.
        """
        import time
        import asyncio
        from app.api.schemas.rag import AnswerConfig, AnswerResult

        start_time = time.perf_counter()

        if config is None:
            config = AnswerConfig()

        # 1. RETRIEVAL PHASE
        retrieval_start = time.perf_counter()
        
        chunks = []
        embedding_tokens = 0

        # Decide retrieval source (custom retrieval groups vs standard)
        if config.retrieval_groups:
            # Query multiple metadata-filtered groups in parallel
            try:
                prompt_embeddings = await self.get_embeddings([question])
                query_vector = prompt_embeddings[0]
                embedding_tokens = len(question.split()) # Estimate of token count

                async def query_group(group):
                    results = self.chroma.query_documents(
                        collection_name=config.collection_name,
                        query_embeddings=[query_vector],
                        n_results=group.n_results,
                        where=group.where
                    )
                    
                    group_chunks = []
                    if results and "documents" in results and results["documents"]:
                        for i in range(len(results["documents"][0])):
                            group_chunks.append(Result(
                                page_content=results["documents"][0][i],
                                metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                            ))
                    return group_chunks

                # Run parallel group queries
                group_results = await asyncio.gather(*(query_group(g) for g in config.retrieval_groups))
                
                # Merge and deduplicate
                seen_content = set()
                for gr in group_results:
                    for chunk in gr:
                        if chunk.page_content not in seen_content:
                            seen_content.add(chunk.page_content)
                            chunks.append(chunk)
            except Exception as e:
                logger.error(f"Group retrieval failed: {e}")
        else:
            # Standard single-collection retrieval
            top_k = config.top_k
            if config.style == "fast" and config.top_k == 15:
                top_k = 5
            
            if config.style == "fast":
                chunks = await self.fetch_context_unranked(question, config.collection_name, retrieval_k=top_k)
            else:
                chunks = await self.fetch_context(question, config.collection_name)

        retrieval_time = (time.perf_counter() - retrieval_start) * 1000.0

        # 2. PROMPT ASSEMBLY
        context_str = "\n\n".join(
            f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
        )

        # Build System Prompt
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

        # Build Messages
        if config.user_template:
            from app.prompts.manager import get_prompt_manager
            pm = get_prompt_manager()
            if config.user_template.endswith(".txt"):
                from app.api.schemas.job_posts import MajorOption, CategoryOption, SkillOption
                
                allowed_majors = []
                seen_majors = set()
                allowed_categories = []
                seen_categories = set()
                available_skills = []
                seen_skills = set()

                for chunk in chunks:
                    meta = chunk.metadata
                    type_val = meta.get("type")
                    if type_val == "major" and "major_id" in meta and "name" in meta:
                        mid = meta["major_id"]
                        if mid not in seen_majors:
                            seen_majors.add(mid)
                            allowed_majors.append(MajorOption(major_id=mid, name=meta["name"]))
                    elif type_val == "category" and "category_id" in meta and "major_id" in meta and "name" in meta:
                        cid = meta["category_id"]
                        if cid not in seen_categories:
                            seen_categories.add(cid)
                            allowed_categories.append(CategoryOption(category_id=cid, major_id=meta["major_id"], name=meta["name"]))
                    elif type_val == "skill" and "skill_id" in meta and "name" in meta:
                        sid = meta["skill_id"]
                        if sid not in seen_skills:
                            seen_skills.add(sid)
                            available_skills.append(SkillOption(skill_id=sid, name=meta["name"]))

                user_prompt = pm.render_prompt(config.user_template, {
                    "client_prompt": question,
                    "allowed_majors": allowed_majors,
                    "allowed_categories": allowed_categories,
                    "available_skills": available_skills,
                    "target_language": "Vietnamese" if any(char in "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ" for char in question) else "English"
                })
            else:
                user_prompt = config.user_template
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        else:
            if config.style == "fast":
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            else:
                messages = [{"role": "system", "content": system_prompt}]
                for msg in config.history:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": question})

        # 3. LLM EXECUTION PHASE
        llm_start = time.perf_counter()
        
        # Determine model & provider dynamically
        model_name = config.model or self.qa_model
        if config.provider and "/" not in model_name:
            model_name = f"{config.provider}/{model_name}"

        completion_kwargs = {
            "model": model_name,
            "messages": messages
        }
        if config.temperature is not None:
            completion_kwargs["temperature"] = config.temperature
        if config.response_format is not None:
            completion_kwargs["response_format"] = config.response_format

        try:
            response = await acompletion(**completion_kwargs)
            raw_answer = response.choices[0].message.content
            usage = getattr(response, "usage", {})
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
        except Exception as e:
            logger.warning(f"LLM call with {model_name} failed: {e}. Trying fallback model {self.fallback_model}.")
            try:
                fallback_kwargs = {
                    "model": self.fallback_model,
                    "messages": messages
                }
                if config.response_format is not None:
                    fallback_kwargs["response_format"] = config.response_format
                response = await acompletion(**fallback_kwargs)
                raw_answer = response.choices[0].message.content
                usage = getattr(response, "usage", {})
                prompt_tokens = getattr(usage, "prompt_tokens", 0)
                completion_tokens = getattr(usage, "completion_tokens", 0)
            except Exception as e2:
                logger.error(f"Fallback LLM call failed: {e2}")
                raise RAGException(f"LLM call failed: {e2}")

        llm_time = (time.perf_counter() - llm_start) * 1000.0

        # Validate structured JSON format if requested
        if config.response_format is not None:
            try:
                answer = config.response_format.model_validate_json(raw_answer)
            except Exception as parse_err:
                logger.error(f"Failed to parse structured JSON response: {parse_err}")
                answer = raw_answer
        else:
            answer = raw_answer

        # 4. METRICS ASSEMBLY
        total_time = (time.perf_counter() - start_time) * 1000.0
        
        sources_list = [
            {"page_content": chunk.page_content, "metadata": chunk.metadata}
            for chunk in chunks
        ]

        return AnswerResult(
            answer=answer,
            sources=sources_list,
            latency_ms=total_time,
            retrieval_time_ms=retrieval_time,
            llm_time_ms=llm_time,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    async def ingest_documents(self, directory_path: Optional[str] = None, collection_name: str = "all") -> int:
        """
        Crawls a directory of markdown files, chunks them semantically, and embeds them.
        If collection_name is "all", it will process each subfolder as a separate collection.
        If collection_name is a specific string, it will only process that specific subfolder into that collection.
        """
        if not directory_path:
            parent_dir = Path(__file__).parent.parent.parent
            kb_path = parent_dir / "knowledge-base"
        else:
            kb_path = Path(directory_path)

        if not kb_path.exists():
            kb_path = Path(__file__).parent.parent.parent / "knowledge-base"
            if not kb_path.exists():
                kb_path = Path(os.getcwd()) / "knowledge-base"
                if not kb_path.exists():
                    os.makedirs(kb_path, exist_ok=True)
                    logger.warning(f"Knowledge base path {kb_path} did not exist. Created empty folder.")
                    return 0

        documents = []
        
        def load_file(file_path: Path, doc_type: str):
            if file_path.suffix == ".md":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        documents.append({
                            "type": doc_type,
                            "source": file_path.as_posix(),
                            "text": f.read()
                        })
                except Exception as fe:
                    logger.error(f"Error reading file {file_path}: {str(fe)}")
            elif file_path.suffix == ".jsonl":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_idx, line in enumerate(f):
                            line = line.strip()
                            if not line:
                                continue
                            data = json.loads(line)
                            text = data.get("text") or data.get("content") or json.dumps(data, ensure_ascii=False)
                            
                            metadata = data.get("metadata", {})
                            for k, v in data.items():
                                if k not in ["metadata"] and not isinstance(v, (dict, list)):
                                    metadata[k] = v
                                    
                            is_small = len(text) < 1000
                            documents.append({
                                "type": doc_type,
                                "source": f"{file_path.as_posix()}:line_{line_idx + 1}",
                                "text": text,
                                "is_pre_chunked": is_small,
                                "chunks": [Chunk(headline=doc_type.replace("-", " ").title(), summary=text[:150], original_text=text)] if is_small else [],
                                "metadata": metadata
                            })
                except Exception as fe:
                    logger.error(f"Error reading file {file_path}: {str(fe)}")

        for entry in kb_path.iterdir():
            if entry.is_dir():
                doc_type = entry.name
                # If specific collection requested, skip other folders
                if collection_name != "all" and doc_type != collection_name:
                    continue
                for ext in ["*.md", "*.jsonl"]:
                    for file in entry.rglob(ext):
                        load_file(file, doc_type)
            elif entry.is_file() and entry.suffix in [".md", ".jsonl"]:
                # General files in root go to "ai-chatbot"
                if collection_name == "all" or collection_name == "ai-chatbot":
                    load_file(entry, "ai-chatbot")

        logger.info(f"Found {len(documents)} markdown documents in {kb_path} to ingest into target: {collection_name}")
        if not documents:
            return 0

        # Group documents by target collection name
        from collections import defaultdict
        docs_by_col = defaultdict(list)
        for doc in documents:
            col = doc["type"]
            docs_by_col[col].append(doc)

        total_chunks = 0
        for col, col_docs in docs_by_col.items():
            logger.info(f"Indexing collection '{col}' with {len(col_docs)} documents...")
            all_chunks: List[Result] = []
            for doc in col_docs:
                chunks = await self.process_document_semantic(doc)
                all_chunks.extend(chunks)

            if not all_chunks:
                continue

            # Generate embeddings and store in Chroma
            texts = [c.page_content for c in all_chunks]
            embeddings = await self.get_embeddings(texts)
            ids = [str(uuid.uuid4()) for _ in all_chunks]
            metadatas = [c.metadata for c in all_chunks]

            # Reset collection if exists
            try:
                self.chroma.delete_collection(col)
            except Exception:
                pass

            try:
                self.chroma.add_documents(
                    collection_name=col,
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                logger.info(f"Vectorstore created/updated with {len(all_chunks)} chunks for collection '{col}'")
                total_chunks += len(all_chunks)
            except Exception as e:
                raise RAGException(f"Failed to add docs to database for collection '{col}': {str(e)}")

        return total_chunks

# Dependency helper
_rag_service = RAGService()

def get_rag_service() -> RAGService:
    return _rag_service
