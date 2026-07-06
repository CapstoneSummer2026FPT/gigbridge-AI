import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from multiprocessing import Pool
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

MODEL = "openai/gpt-4.1-nano"
FALLBACK_MODEL = "gpt-4o-mini"

# Database name matching user configuration parent.parent / "preprocessed_db"
# If default_db_path starts with "." we resolve relative to current file directory
if default_db_path.startswith("."):
    DB_NAME = str(Path(__file__).parent / default_db_path.lstrip("./"))
else:
    DB_NAME = default_db_path

collection_name = "docs"
embedding_model = default_embedding_model
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"
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
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )

class Chunks(BaseModel):
    chunks: list[Chunk]

def fetch_documents():
    """A homemade version of the LangChain DirectoryLoader"""
    documents = []

    if not KNOWLEDGE_BASE_PATH.exists():
        print(f"Knowledge base path does not exist at {KNOWLEDGE_BASE_PATH}. Creating directory...")
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        return documents

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        if folder.is_dir():
            doc_type = folder.name
            for file in folder.rglob("*.md"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        documents.append({"type": doc_type, "source": file.as_posix(), "text": f.read()})
                except Exception as e:
                    print(f"Error reading file {file}: {e}")
        elif folder.is_file() and folder.suffix == ".md":
            try:
                with open(folder, "r", encoding="utf-8") as f:
                    documents.append({"type": "general", "source": folder.as_posix(), "text": f.read()})
            except Exception as e:
                print(f"Error reading file {folder}: {e}")

    print(f"Loaded {len(documents)} documents")
    return documents

def make_prompt(document):
    how_many = (len(document["text"]) // AVERAGE_CHUNK_SIZE) + 1
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

def make_messages(document):
    return [
        {"role": "user", "content": make_prompt(document)},
    ]

@retry(wait=wait)
def process_document(document):
    messages = make_messages(document)
    try:
        response = completion(model=MODEL, messages=messages, response_format=Chunks)
        reply = response.choices[0].message.content
    except Exception as e:
        print(f"Warning: model {MODEL} failed ({e}). Retrying semantic chunking with fallback model {FALLBACK_MODEL}...")
        try:
            response = completion(model=FALLBACK_MODEL, messages=messages, response_format=Chunks)
            reply = response.choices[0].message.content
        except Exception as e2:
            print(f"Error: Fallback model failed too ({e2}). Skipping document {document['source']}.")
            return []
            
    try:
        doc_as_chunks = Chunks.model_validate_json(reply).chunks
        return [chunk.as_result(document) for chunk in doc_as_chunks]
    except Exception as parse_err:
        print(f"Error parsing JSON from response for doc {document['source']}: {parse_err}")
        return []

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

def create_embeddings(chunks):
    if not chunks:
        print("No chunks to index.")
        return
        
    chroma = PersistentClient(path=DB_NAME)
    if collection_name in [c.name for c in chroma.list_collections()]:
        chroma.delete_collection(collection_name)

    texts = [chunk.page_content for chunk in chunks]
    
    # Check if OpenAI key is configured
    if not openai:
        # Fallback to Gemini OpenAI compatible embedding endpoint if GEMINI_API_KEY exists
        if gemini_key:
            print("Using Google Gemini API for generating embeddings...")
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
        print(f"Generating embeddings using model: {embedding_model}")
        emb = openai.embeddings.create(model=embedding_model, input=texts).data
        vectors = [e.embedding for e in emb]

    collection = chroma.get_or_create_collection(collection_name)

    ids = [str(i) for i in range(len(chunks))]
    metas = [chunk.metadata for chunk in chunks]

    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metas)
    print(f"Vectorstore created with {collection.count()} documents at {DB_NAME}")

if __name__ == "__main__":
    documents = fetch_documents()
    if not documents:
        print("No documents found in knowledge-base folder. Please add markdown (*.md) files inside the knowledge-base directory.")
        sys.exit(0)
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")
