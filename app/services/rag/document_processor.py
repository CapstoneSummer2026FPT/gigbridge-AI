"""
PURPOSE: Text chunking, recursive boundary splitting, and semantic document summary processing for RAG indexing.
IMPORTANCE: High — Responsible for converting raw knowledge documents into search-optimized text chunks.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/document_processor.py -> app/services/rag/query_engine.py
"""

import asyncio
import logging
from typing import Any, Dict, List
from litellm import acompletion

from app.services.rag.rag_base import ChunkMetadata, RAGBaseService, Result

logger = logging.getLogger("ai_server.document_processor")


class DocumentProcessorService(RAGBaseService):
    """Handles text chunking and hybrid semantic chunk summarization."""

    async def process_document_semantic(self, document: Dict[str, Any]) -> List[Result]:
        """Split a document semantically using recursive splitting followed by LLM headline/summary generation.
        
        Flow:
        1. Check if document is pre-chunked.
        2. Split text recursively using paragraph, line, sentence, and word boundaries.
        3. Concurrently invoke cheap LLM to generate search-optimized headline & 1-2 sentence summary.
        4. Package into Result models and return list.
        """
        if document.get("is_pre_chunked"):
            return [chunk.as_result(document) for chunk in document["chunks"]]

        raw_chunks = self.split_text_recursive(document["text"])
        sem = asyncio.Semaphore(15)

        async def process_single_chunk(chunk_text: str) -> Result:
            metadata = {"source": document.get("source", ""), "type": document.get("type", "")}
            if "metadata" in document and isinstance(document["metadata"], dict):
                metadata.update(document["metadata"])

            prompt = self.make_chunk_summary_prompt(chunk_text, document["type"], document["source"])
            messages = [{"role": "user", "content": prompt}]

            headline = document["type"].replace("-", " ").title()
            summary = chunk_text[:150]

            async with sem:
                try:
                    response = await acompletion(
                        model=self.chunk_model,
                        messages=messages,
                        response_format=ChunkMetadata
                    )
                    reply = response.choices[0].message.content
                    meta = ChunkMetadata.model_validate_json(reply)
                    headline = meta.headline
                    summary = meta.summary
                except Exception as e:
                    logger.warning(
                        f"Chunk summary with {self.chunk_model} failed: {str(e)}. Retrying with {self.fallback_model}..."
                    )
                    try:
                        response = await acompletion(
                            model=self.fallback_model,
                            messages=messages,
                            response_format=ChunkMetadata
                        )
                        reply = response.choices[0].message.content
                        meta = ChunkMetadata.model_validate_json(reply)
                        headline = meta.headline
                        summary = meta.summary
                    except Exception as e2:
                        logger.error(f"LLM metadata generation failed completely: {str(e2)}. Using fallback values.")

            page_content = f"{headline}\n\n{summary}\n\n{chunk_text}"
            return Result(page_content=page_content, metadata=metadata)

        tasks = [process_single_chunk(c) for c in raw_chunks]
        results = await asyncio.gather(*tasks)
        return list(results)

    def split_text_recursive(self, text: str, max_chars: int = 1200, overlap: int = 300) -> List[str]:
        """Recursively split text using paragraph, line, sentence, and word boundaries.
        
        Guarantees chunks do not exceed max_chars while preserving context overlap across boundaries.
        """
        if len(text) <= max_chars:
            return [text]

        separators = ["\n\n", "\n", ". ", " ", ""]

        def _split(txt: str, separators: List[str]) -> List[str]:
            if len(txt) <= max_chars or not separators:
                return [txt]

            sep = separators[0]
            splits = txt.split(sep)

            chunks = []
            current_chunk = []
            current_len = 0

            for part in splits:
                part_len = len(part)
                if part_len > max_chars:
                    if current_chunk:
                        chunks.append(sep.join(current_chunk))
                        current_chunk = []
                        current_len = 0
                    sub_chunks = _split(part, separators[1:])
                    chunks.extend(sub_chunks)
                else:
                    added_len = part_len + (len(sep) if current_chunk else 0)
                    if current_len + added_len <= max_chars:
                        current_chunk.append(part)
                        current_len += added_len
                    else:
                        if current_chunk:
                            chunks.append(sep.join(current_chunk))
                        current_chunk = [part]
                        current_len = part_len

            if current_chunk:
                chunks.append(sep.join(current_chunk))

            return [c for c in chunks if c.strip()]

        raw_chunks = _split(text, separators)

        merged_chunks = []
        for i, chunk in enumerate(raw_chunks):
            if i == 0:
                merged_chunks.append(chunk)
                continue

            prev_chunk = raw_chunks[i - 1]
            overlap_text = prev_chunk[-overlap:]
            space_idx = overlap_text.find(" ")
            if space_idx != -1:
                overlap_text = overlap_text[space_idx + 1:]

            merged_chunks.append(overlap_text + "\n" + chunk)

        return merged_chunks

    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks using word count windows."""
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

    @staticmethod
    def make_chunk_summary_prompt(chunk_text: str, doc_type: str, source: str) -> str:
        """Construct Jinja/string prompt for generating search headline and chunk summary."""
        return f"""
You are an AI assistant processing documentation for a company called GigBridge.

Here is a specific text chunk from a document of type '{doc_type}' retrieved from '{source}':

---
{chunk_text}
---

Generate:
1. A search-optimized headline (3-5 words) that is most likely to match queries for this content.
2. A brief 1-2 sentence summary of the key facts in this chunk.

Respond in JSON format matching the schema.
"""
