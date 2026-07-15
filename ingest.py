import os
import sys
import json
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion, acompletion
from multiprocessing import Pool
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

MODEL = "openai/gpt-4.1-nano"
FALLBACK_MODEL = "gpt-4o-mini"

# Database name matching user configuration parent.parent / "preprocessed_db"
# If default_db_path starts with "." we resolve relative to current file directory
if default_db_path.startswith("."):
    DB_NAME = str(Path(__file__).parent / default_db_path.lstrip("./"))
else:
    DB_NAME = default_db_path

collection_name = "ai-chatbot"
embedding_model = default_embedding_model
KNOWLEDGE_BASE_PATH = Path(__file__).parent / "knowledge-base"
AVERAGE_CHUNK_SIZE = 100
wait = wait_exponential(multiplier=1, min=10, max=240)

WORKERS = 1

class Result(BaseModel):
    page_content: str
    metadata: dict

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

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )

class Chunks(BaseModel):
    chunks: list[Chunk]

class ChunkMetadata(BaseModel):
    headline: str = Field(
        description="A brief search-optimized heading for this chunk, typically a few words, that is most likely to match queries for this content"
    )
    summary: str = Field(
        description="A 1-2 sentence summary of this chunk's key facts"
    )

def fetch_documents():
    """A homemade version of the LangChain DirectoryLoader supporting both Markdown and JSONL"""
    documents = []

    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"Knowledge base path does not exist at {KNOWLEDGE_BASE_PATH}. Creating directory...")
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        return documents

    def load_file(file_path, doc_type):
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
                        text = data.get("text") or data.get("content") or json.dumps(data, ensure_ascii=False)
                        
                        metadata = data.get("metadata", {})
                        for k, v in data.items():
                            if k not in ["metadata"] and not isinstance(v, (dict, list)):
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

def split_text_recursive(text: str, max_chars: int = 1200, overlap: int = 300) -> list[str]:
    """
    Recursively splits text using paragraph, line, sentence, and word boundaries
    to create chunks of at most max_chars with overlap.
    """
    if len(text) <= max_chars:
        return [text]

    # Separators from largest to smallest
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    def _split(txt: str, separators: list[str]) -> list[str]:
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
                # Flush current chunk first
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
    
    # Apply overlap merging
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

def make_chunk_summary_prompt(chunk_text: str, doc_type: str, source: str) -> str:
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

async def process_document_async(document):
    raw_chunks = split_text_recursive(document["text"])
    
    # Limit concurrency to 15 parallel requests
    sem = asyncio.Semaphore(15)
    
    async def process_single_chunk(chunk_text: str) -> Result:
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
            
        prompt = make_chunk_summary_prompt(chunk_text, document["type"], document["source"])
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
                reply = response.choices[0].message.content
                meta = ChunkMetadata.model_validate_json(reply)
                headline = meta.headline
                summary = meta.summary
            except Exception as e:
                print(f"Warning: model {MODEL} failed ({e}) on chunk summary. Retrying with fallback model {FALLBACK_MODEL}...")
                try:
                    response = await acompletion(
                        model=FALLBACK_MODEL,
                        messages=messages,
                        response_format=ChunkMetadata
                    )
                    reply = response.choices[0].message.content
                    meta = ChunkMetadata.model_validate_json(reply)
                    headline = meta.headline
                    summary = meta.summary
                except Exception as e2:
                    print(f"Error: Fallback model failed too ({e2}) on chunk summary. Using fallback values.")
        
        page_content = f"{headline}\n\n{summary}\n\n{chunk_text}"
        return Result(page_content=page_content, metadata=metadata)
        
    tasks = [process_single_chunk(c) for c in raw_chunks]
    results = await asyncio.gather(*tasks)
    return list(results)

def process_document(document):
    if document.get("is_pre_chunked"):
        metadata = {"source": document["source"], "type": document["type"]}
        if "metadata" in document and isinstance(document["metadata"], dict):
            metadata.update(document["metadata"])
        return [Result(page_content=document["text"], metadata=metadata)]
        
    return asyncio.run(process_document_async(document))

def create_chunks(documents):
    """
    Create chunks using a number of workers in parallel.
    If you get a rate limit error, set the WORKERS to 1.
    """
    chunks = []
    if not documents:
        return chunks
        
    # Standard sequential processing if WORKERS <= 1 or only 1 document
    if WORKERS <= 1 or len(documents) == 1:
        for doc in tqdm(documents):
            chunks.extend(process_document(doc))
        return chunks
        
    try:
        with Pool(processes=WORKERS) as pool:
            for result in tqdm(pool.imap_unordered(process_document, documents), total=len(documents)):
                chunks.extend(result)
    except Exception as e:
        print(f"Warning: Multiprocessing Pool failed ({e}). Falling back to sequential execution...")
        for doc in tqdm(documents):
            chunks.extend(process_document(doc))
            
    return chunks

def create_embeddings(chunks, target_collection_name):
    if not chunks:
        print(f"No chunks to index for collection: {target_collection_name}.")
        return
        
    chroma = PersistentClient(path=DB_NAME)
    if target_collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(target_collection_name)

    texts = [chunk.page_content for chunk in chunks]
    
    # Check if OpenAI key is configured
    if not openai:
        # Fallback to Gemini OpenAI compatible embedding endpoint if GEMINI_API_KEY exists
        if gemini_key:
            print(f"Using Google Gemini API for generating embeddings in collection '{target_collection_name}'...")
            try:
                from openai import OpenAI as GeminiOpenAI
                gemini_client = GeminiOpenAI(
                    api_key=gemini_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                model = "text-embedding-004"
                emb = gemini_client.embeddings.create(model=model, input=texts).data
                vectors = [e.embedding for e in emb]
            except Exception as e:
                print(f"Gemini embeddings failed: {e}")
                raise e
        else:
            raise ValueError("No API Key configured for generating embeddings. Set OPENAI_API_KEY or GEMINI_API_KEY in .env.")
    else:
        print(f"Generating embeddings for collection '{target_collection_name}' using model: {embedding_model}")
        emb = openai.embeddings.create(model=embedding_model, input=texts).data
        vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(target_collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created/updated with {collection.count()} documents at {DB_NAME} (Collection: {target_collection_name})")

if __name__ == "__main__":
    documents = fetch_documents()
    if not documents:
        print("No documents found in knowledge-base folder. Please add markdown (*.md) files inside the knowledge-base directory.")
        sys.exit(0)
        
    # Group documents by their folder/type
    from collections import defaultdict
    docs_by_collection = defaultdict(list)
    for doc in documents:
        col_name = doc["type"] if doc["type"] != "general" else "ai-chatbot"
        docs_by_collection[col_name].append(doc)
        
    for col_name, col_docs in docs_by_collection.items():
        print(f"\nProcessing collection: '{col_name}' ({len(col_docs)} documents)...")
        chunks = create_chunks(col_docs)
        create_embeddings(chunks, col_name)
        
    print("\nIngestion complete")
