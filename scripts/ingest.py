"""
PURPOSE: Knowledge base document ingestion, semantic chunking, and vector embedding creation runner script.
IMPORTANCE: High — Ingests markdown and JSONL taxonomy data from knowledge-base folder into Chroma DB vector collections.
READING FLOW: app/services/rag/rag_base.py -> app/services/rag/document_processor.py -> scripts/ingest.py
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

from chromadb import PersistentClient
from dotenv import load_dotenv
from litellm import acompletion
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm

load_dotenv(override=True)

try:
    from app.core.config import settings
    default_db_path = settings.CHROMA_DB_PATH
    default_embedding_model = settings.EMBEDDING_MODEL
    openai_key = settings.OPENAI_API_KEY
    gemini_key = settings.GEMINI_API_KEY
    claude_key = settings.CLAUDE_API_KEY
except ImportError:
    default_db_path = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
    default_embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    claude_key = os.getenv("CLAUDE_API_KEY", "")

openai_client = OpenAI(api_key=openai_key) if openai_key else None

if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key
if claude_key:
    os.environ["ANTHROPIC_API_KEY"] = claude_key

MODEL = "openai/gpt-4.1-nano"
FALLBACK_MODEL = "gpt-4o-mini"

if default_db_path.startswith("."):
    DB_NAME = str(Path(__file__).resolve().parents[1] / default_db_path.lstrip("./"))
else:
    DB_NAME = default_db_path

KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parents[1] / "knowledge-base"


class Result(BaseModel):
    page_content: str
    metadata: dict


class Chunk(BaseModel):
    headline: str = Field(description="A brief search-optimized heading for this chunk")
    summary: str = Field(description="A few sentences summarizing chunk content")
    original_text: str = Field(description="Original text of this chunk")

    def as_result(self, document: dict) -> Result:
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return Result(
            page_content=f"{self.headline}\n\n{self.summary}\n\n{self.original_text}",
            metadata=metadata,
        )


class ChunkMetadata(BaseModel):
    headline: str = Field(description="Search-optimized headline")
    summary: str = Field(description="1-2 sentence summary")


def main() -> None:
    """Execute knowledge base ingestion pipeline across collections."""
    documents = fetch_documents()
    if not documents:
        print("No documents found in knowledge-base folder.")
        sys.exit(0)

    docs_by_collection = defaultdict(list)
    for doc in documents:
        col_name = doc["type"] if doc["type"] != "general" else "ai-chatbot"
        docs_by_collection[col_name].append(doc)

    for col_name, col_docs in docs_by_collection.items():
        print(f"\nProcessing collection: '{col_name}' ({len(col_docs)} documents)...")
        chunks = create_chunks(col_docs)
        create_embeddings(chunks, col_name)

    print("\nIngestion complete")


def fetch_documents() -> list[dict]:
    """Load markdown and JSONL files from knowledge-base directory."""
    documents = []
    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"Knowledge base path does not exist at {KNOWLEDGE_BASE_PATH}. Creating directory...")
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        return documents

    def load_file(file_path: Path, doc_type: str) -> None:
        if file_path.suffix == ".md":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    documents.append({
                        "type": doc_type,
                        "source": file_path.as_posix(),
                        "text": f.read(),
                        "is_pre_chunked": False
                    })
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        elif file_path.suffix == ".jsonl":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f):
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        type_val = data.get("type")
                        if type_val == "major":
                            text = f"Major: {data.get('name', '')}"
                        elif type_val == "category":
                            text = f"Category: {data.get('name', '')}"
                        elif type_val == "skill":
                            text = f"Skill: {data.get('name', '')}"
                        else:
                            text = data.get("text") or data.get("content") or json.dumps(data, ensure_ascii=False)

                        metadata = data.get("metadata", {})
                        for k, v in data.items():
                            if k != "metadata" and not isinstance(v, (dict, list)):
                                metadata[k] = v

                        documents.append({
                            "type": doc_type,
                            "source": f"{file_path.as_posix()}:line_{line_idx + 1}",
                            "text": text,
                            "is_pre_chunked": True,
                            "metadata": metadata
                        })
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        if folder.is_dir():
            doc_type = folder.name
            for ext in ["*.md", "*.jsonl"]:
                for file in folder.rglob(ext):
                    load_file(file, doc_type)
        elif folder.is_file() and folder.suffix in [".md", ".jsonl"]:
            load_file(folder, "ai-chatbot")

    print(f"Loaded {len(documents)} documents")
    return documents


def create_chunks(documents: list[dict]) -> list[Result]:
    """Create semantic chunks for a list of document dictionaries."""
    chunks = []
    for doc in tqdm(documents):
        chunks.extend(process_document(doc))
    return chunks


def process_document(document: dict) -> list[Result]:
    """Process single document into list of Result items."""
    if document.get("is_pre_chunked"):
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return [Result(page_content=document["text"], metadata=metadata)]

    return asyncio.run(process_document_async(document))


async def process_document_async(document: dict) -> list[Result]:
    """Asynchronously process document text into semantic chunks with LLM headlines."""
    raw_chunks = split_text_recursive(document["text"])
    sem = asyncio.Semaphore(15)

    async def process_single_chunk(chunk_text: str) -> Result:
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])

        prompt = f"Summarize key facts in chunk: {chunk_text[:300]}"
        messages = [{"role": "user", "content": prompt}]
        headline = document["type"].replace("-", " ").title()
        summary = chunk_text[:150]

        async with sem:
            try:
                response = await acompletion(
                    model=MODEL,
                    messages=messages,
                    response_format=ChunkMetadata
                )
                meta = ChunkMetadata.model_validate_json(response.choices[0].message.content)
                headline = meta.headline
                summary = meta.summary
            except Exception:
                pass

        page_content = f"{headline}\n\n{summary}\n\n{chunk_text}"
        return Result(page_content=page_content, metadata=metadata)

    tasks = [process_single_chunk(c) for c in raw_chunks]
    return list(await asyncio.gather(*tasks))


def split_text_recursive(text: str, max_chars: int = 1200, overlap: int = 300) -> list[str]:
    """Split text recursively across paragraph and line boundaries."""
    if len(text) <= max_chars:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(txt: str, seps: list[str]) -> list[str]:
        if len(txt) <= max_chars or not seps:
            return [txt]
        sep = seps[0]
        splits = txt.split(sep)
        chunks = []
        curr = []
        curr_len = 0
        for part in splits:
            if len(part) > max_chars:
                if curr:
                    chunks.append(sep.join(curr))
                    curr = []
                    curr_len = 0
                chunks.extend(_split(part, seps[1:]))
            else:
                add_len = len(part) + (len(sep) if curr else 0)
                if curr_len + add_len <= max_chars:
                    curr.append(part)
                    curr_len += add_len
                else:
                    if curr:
                        chunks.append(sep.join(curr))
                    curr = [part]
                    curr_len = len(part)
        if curr:
            chunks.append(sep.join(curr))
        return [c for c in chunks if c.strip()]

    raw_chunks = _split(text, separators)
    merged = []
    for i, chunk in enumerate(raw_chunks):
        if i == 0:
            merged.append(chunk)
            continue
        prev = raw_chunks[i - 1]
        ov = prev[-overlap:]
        sp = ov.find(" ")
        if sp != -1:
            ov = ov[sp + 1:]
        merged.append(ov + "\n" + chunk)
    return merged


def create_embeddings(chunks: list[Result], target_collection_name: str) -> None:
    """Generate embeddings and write chunks to persistent Chroma collection."""
    if not chunks:
        return

    chroma = PersistentClient(path=DB_NAME)
    if target_collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(target_collection_name)

    texts = [chunk.page_content for chunk in chunks]
    if not openai_client:
        raise ValueError("OpenAI API key missing")

    emb = openai_client.embeddings.create(model=default_embedding_model, input=texts).data
    vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(target_collection_name)
    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]
    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Collection '{target_collection_name}' updated with {collection.count()} items.")


if __name__ == "__main__":
    main()
