import os
import argparse
from pathlib import Path
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from litellm import completion
from tenacity import retry, wait_exponential, stop_after_attempt

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

collection_name = "general-knowledge"
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
{context}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""

class Result(BaseModel):
    page_content: str
    metadata: dict

class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )

class RelevanceCheck(BaseModel):
    related: bool = Field(description="True if the message is related to GigBridge; False otherwise.")
    topic: str = Field(description="The main topic/subject of the query in the user's language.")
    language: str = Field(description="The language of the user's message: 'vi' or 'en'.")

def check_relevance(question: str, history: list[dict] = []) -> RelevanceCheck:
    """Check if the question is related to GigBridge."""
    system_prompt = """You are a classifier for the GigBridge assistant.
Determine if the user's message is a query or statement related to the company GigBridge, its services, features, platform, job posts, talent matching, candidate vetting, or content in the GigBridge knowledge base.
Greeting messages (like "hello", "hi", "xin chào") or questions about what you can do/what is your purpose are considered RELATED.
General knowledge questions, history, coding questions not about GigBridge, arithmetic, or requests about unrelated subjects are UNRELATED.

You must respond ONLY with a JSON object matching this schema:
{
  "related": true/false,
  "topic": "the main topic/subject of the query in the user's language, e.g. 'sự kiện Thiên An Môn' or 'what happened in Tiananmen'",
  "language": "vi" (Vietnamese) or "en" (English)
}
"""
    history_str = str(history) if history else "[]"
    user_prompt = f"Conversation History:\n{history_str}\n\nUser Question:\n{question}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = completion(model=MODEL, messages=messages, response_format=RelevanceCheck)
        reply = response.choices[0].message.content
        return RelevanceCheck.model_validate_json(reply)
    except Exception as e:
        print(f"Warning: Relevance check with {MODEL} failed ({e}). Trying fallback {FALLBACK_MODEL}...")
        try:
            response = completion(model=FALLBACK_MODEL, messages=messages, response_format=RelevanceCheck)
            reply = response.choices[0].message.content
            return RelevanceCheck.model_validate_json(reply)
        except Exception as e2:
            print(f"Error: Relevance check failed completely ({e2}). Defaulting to related=True.")
            is_vi = any(char in "áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ" for char in question)
            return RelevanceCheck(related=True, topic="", language="vi" if is_vi else "en")


@retry(
    wait=wait_exponential(multiplier=1, min=10, max=240),
    stop=stop_after_attempt(5),
    reraise=True
)
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

@retry(
    wait=wait_exponential(multiplier=1, min=10, max=240),
    stop=stop_after_attempt(5),
    reraise=True
)
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

@retry(
    wait=wait_exponential(multiplier=1, min=10, max=240),
    stop=stop_after_attempt(5),
    reraise=True
)
def answer_question(question: str, history: list[dict] = [], style: str = "precision") -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context
    """
    # Relevance check to filter off-topic questions
    rel = check_relevance(question, history)
    if not rel.related:
        topic = rel.topic or ("this topic" if rel.language == "en" else "chủ đề này")
        if rel.language == "vi":
            answer = f"Xin lỗi, nhưng tôi không có thông tin nào về {topic}. Tôi chỉ có thể cung cấp thông tin liên quan đến GigBridge. Nếu bạn có câu hỏi nào về GigBridge, hãy cho tôi biết!"
        else:
            answer = f"Sorry, but I don't have any information about {topic}. I can only provide information related to GigBridge. If you have any questions about GigBridge, please let me know!"
        return answer, []

    if style == "fast":
        chunks = fetch_context_unranked(question)[:5]
        context = "\n\n".join(
            f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}" for chunk in chunks
        )
        system_prompt = SYSTEM_PROMPT.format(context=context)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    else:
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
    parser.add_argument("--style", type=str, choices=["precision", "fast"], default="precision", help="The QA style/mode to use")
    parser.add_argument("--collection", type=str, default="general-knowledge", help="Chroma DB collection name")
    args = parser.parse_args()

    try:
        collection_name = args.collection
        collection = chroma.get_or_create_collection(collection_name)
        print(f"Answering query: '{args.query}' (Collection: {collection_name}, Style: {args.style})...")
        answer, context = answer_question(args.query, style=args.style)
        print("\n=== ANSWER ===")
        print(answer)
        print("\n=== SOURCES ===")
        for idx, doc in enumerate(context):
            print(f"[{idx+1}] {doc.metadata.get('source', 'unknown')} (Type: {doc.metadata.get('type', 'unknown')})")
    except Exception as err:
        print(f"\nExecution failed: {err}")
