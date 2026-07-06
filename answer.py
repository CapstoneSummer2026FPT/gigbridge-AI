import os
import argparse
from pathlib import Path
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from litellm import completion
from tenacity import retry, wait_exponential

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

# Try loading from app config if available
try:
    from app.core.config import settings
    default_db_path = settings.CHROMA_DB_PATH
    default_embedding_model = settings.EMBEDDING_MODEL
    openai_key = settings.OPENAI_API_KEY
    gemini_key = settings.GEMINI_API_KEY
    claude_key = settings.CLAUDE_API_KEY
except ImportError:
    default_db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    default_embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    claude_key = os.getenv("CLAUDE_API_KEY", "")

# Initialize OpenAI client manually for embeddings
from openai import OpenAI
openai = OpenAI(api_key=openai_key) if openai_key else None

# Set up environment for litellm
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key
if gemini_key:
    os.environ["GEMINI_API_KEY"] = gemini_key
if claude_key:
    os.environ["ANTHROPIC_API_KEY"] = claude_key

MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "gpt-4o-mini"

# Database path resolution
if default_db_path.startswith("."):
    DB_NAME = str(Path(__file__).parent / default_db_path.lstrip("./"))
else:
    DB_NAME = default_db_path

collection_name = "docs"
embedding_model = default_embedding_model
wait = wait_exponential(multiplier=1, min=10, max=240)

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(collection_name)

RETRIEVAL_K = 20
FINAL_K = 10

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company GigBridge.
You are chatting with a user about GigBridge.
Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
If you don't know the answer, say so.
For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{{context}}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""

class Result(BaseModel):
    page_content: str
    metadata: dict

class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )

@retry(wait=wait)
def rerank(question, chunks):
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
        response = completion(model=MODEL, messages=messages, response_format=RankOrder)
        reply = response.choices[0].message.content
        order = RankOrder.model_validate_json(reply).order
    except Exception as e:
        print(f"Warning: model {MODEL} failed to rerank ({e}). Trying fallback model {FALLBACK_MODEL}...")
        try:
            response = completion(model=FALLBACK_MODEL, messages=messages, response_format=RankOrder)
            reply = response.choices[0].message.content
            order = RankOrder.model_validate_json(reply).order
        except Exception as e2:
            print(f"Error: Reranker failed completely ({e2}). Using default collection order.")
            return chunks[:FINAL_K]
            
    try:
        return [chunks[i - 1] for i in order if 0 <= i - 1 < len(chunks)]
    except Exception as parse_err:
        print(f"Error ordering chunks: {parse_err}. Using default collection order.")
        return chunks[:FINAL_K]

def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )

@retry(wait=wait)
def rewrite_query(question, history=[]):
    """Rewrite the user's question to be a more specific question that is more likely to surface relevant content in the Knowledge Base."""
    message = f"""
You are in a conversation with a user, answering questions about the company GigBridge.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
    try:
        response = completion(model=MODEL, messages=[{"role": "system", "content": message}])
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Warning: query rewrite with {MODEL} failed ({e}). Trying fallback {FALLBACK_MODEL}...")
        try:
            response = completion(model=FALLBACK_MODEL, messages=[{"role": "system", "content": message}])
            return response.choices[0].message.content.strip()
        except Exception:
            return question

def merge_chunks(chunks, reranked):
    merged = chunks[:]
    existing = [chunk.page_content for chunk in chunks]
    for chunk in reranked:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged

def fetch_context_unranked(question):
    # Check if OpenAI client is set
    if not openai:
        # Fallback to Gemini OpenAI compatible endpoint if GEMINI_API_KEY exists
        if gemini_key:
            from openai import OpenAI as GeminiOpenAI
            gemini_client = GeminiOpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            model = "text-embedding-004"
            query = gemini_client.embeddings.create(model=model, input=[question]).data[0].embedding
        else:
            raise ValueError("No API Key configured for generating embeddings. Set OPENAI_API_KEY or GEMINI_API_KEY in .env.")
    else:
        query = openai.embeddings.create(model=embedding_model, input=[question]).data[0].embedding
        
    results = collection.query(query_embeddings=[query], n_results=RETRIEVAL_K)
    chunks = []
    if results and results["documents"] and len(results["documents"]) > 0:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            chunks.append(Result(page_content=doc, metadata=meta or {}))
    return chunks

def fetch_context(original_question):
    rewritten_question = rewrite_query(original_question)
    print(f"Rewritten query: {rewritten_question}")
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(rewritten_question)
    chunks = merge_chunks(chunks1, chunks2)
    reranked = rerank(original_question, chunks)
    return reranked[:FINAL_K]

@retry(wait=wait)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context
    """
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    try:
        response = completion(model=MODEL, messages=messages)
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"Warning: QA with {MODEL} failed ({e}). Trying fallback {FALLBACK_MODEL}...")
        try:
            response = completion(model=FALLBACK_MODEL, messages=messages)
            answer = response.choices[0].message.content
        except Exception as e2:
            print(f"Error: QA failed completely ({e2}).")
            raise e2
            
    return answer, chunks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask questions to the GigBridge Knowledge Base.")
    parser.add_argument("--query", type=str, required=True, help="Question to ask")
    args = parser.parse_args()

    try:
        print(f"Answering query: '{args.query}'...")
        answer, context = answer_question(args.query)
        print("\n=== ANSWER ===")
        print(answer)
        print("\n=== SOURCES ===")
        for idx, doc in enumerate(context):
            print(f"[{idx+1}] {doc.metadata.get('source', 'unknown')} (Type: {doc.metadata.get('type', 'unknown')})")
    except Exception as err:
        print(f"\nExecution failed: {err}")
