"""
PURPOSE: CLI Knowledge Base Question Answering runner script querying Chroma DB vector collections.
IMPORTANCE: High — Provides command-line interface for querying RAG knowledge bases directly.
READING FLOW: app/services/rag/query_engine.py -> scripts/answer.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from chromadb import PersistentClient
from dotenv import load_dotenv
from litellm import completion
from openai import OpenAI
from pydantic import BaseModel, Field

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

MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "gpt-4o-mini"

if default_db_path.startswith("."):
    DB_NAME = str(Path(__file__).resolve().parents[1] / default_db_path.lstrip("./"))
else:
    DB_NAME = default_db_path

collection_name = "general-knowledge"
embedding_model = default_embedding_model

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

RETRIEVAL_K = 20
FINAL_K = 10


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(description="Order of relevance by chunk id number")


class RelevanceCheck(BaseModel):
    related: bool = Field(description="True if message is related to GigBridge")
    topic: str = Field(description="Main topic/subject of the query")
    language: str = Field(description="Language of message: 'vi' or 'en'")


def main() -> None:
    """CLI entrypoint for interactive QA queries."""
    parser = argparse.ArgumentParser(description="Ask questions to the GigBridge Knowledge Base.")
    parser.add_argument("--query", type=str, required=True, help="Question to ask")
    parser.add_argument("--style", type=str, choices=["precision", "fast"], default="precision", help="QA style mode")
    parser.add_argument("--collection", type=str, default="general-knowledge", help="Chroma DB collection name")
    args = parser.parse_args()

    try:
        global collection
        collection = chroma.get_or_create_collection(args.collection)
        print(f"Answering query: '{args.query}' (Collection: {args.collection}, Style: {args.style})...")
        answer, context = answer_question(args.query, style=args.style)
        print("\n=== ANSWER ===")
        print(answer)
        print("\n=== SOURCES ===")
        for idx, doc in enumerate(context):
            print(f"[{idx+1}] {doc.metadata.get('source', 'unknown')} (Type: {doc.metadata.get('type', 'unknown')})")
    except Exception as err:
        print(f"\nExecution failed: {err}")


def answer_question(question: str, history: list[dict] = [], style: str = "precision") -> tuple[str, list]:
    """Execute RAG question answering flow."""
    rel = check_relevance(question, history)
    if not rel.related:
        topic = rel.topic or ("this topic" if rel.language == "en" else "chủ đề này")
        if rel.language == "vi":
            answer = f"Xin lỗi, nhưng tôi không có thông tin nào về {topic}. Tôi chỉ có thể cung cấp thông tin liên quan đến GigBridge."
        else:
            answer = f"Sorry, but I don't have any information about {topic}. I can only provide information related to GigBridge."
        return answer, []

    if style == "fast":
        chunks = fetch_context_unranked(question)[:5]
        context = "\n\n".join(
            f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
        )
        system_prompt = f"Answer questions using context:\n{context}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    else:
        chunks = fetch_context(question)
        context = "\n\n".join(
            f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
        )
        system_prompt = f"Answer questions accurately using context:\n{context}"
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": question}]

    try:
        response = completion(model=MODEL, messages=messages)
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"Warning: QA with {MODEL} failed ({e}). Trying fallback {FALLBACK_MODEL}...")
        response = completion(model=FALLBACK_MODEL, messages=messages)
        answer = response.choices[0].message.content

    return answer, chunks


def check_relevance(question: str, history: list[dict] = []) -> RelevanceCheck:
    """Classify if question is related to GigBridge platform."""
    system_prompt = "Determine if user message is related to GigBridge services or knowledge base."
    user_prompt = f"User Question: {question}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    try:
        response = completion(model=MODEL, messages=messages, response_format=RelevanceCheck)
        return RelevanceCheck.model_validate_json(response.choices[0].message.content)
    except Exception:
        is_vi = any(char in "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ" for char in question)
        return RelevanceCheck(related=True, topic="", language="vi" if is_vi else "en")


def fetch_context(original_question: str) -> list[Result]:
    """Retrieve dual-query unranked context and rerank via LLM."""
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(original_question)
    merged = chunks1[:]
    existing = {c.page_content for c in chunks1}
    for c in chunks2:
        if c.page_content not in existing:
            merged.append(c)
    return merged[:FINAL_K]


def fetch_context_unranked(question: str) -> list[Result]:
    """Embed question and query Chroma DB collection."""
    if not openai_client:
        raise ValueError("OpenAI client missing")
    query = openai_client.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    if results and results["documents"] and len(results["documents"]) > 0:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            chunks.append(Result(page_content=doc, metadata=meta or {}))
    return chunks


if __name__ == "__main__":
    main()
