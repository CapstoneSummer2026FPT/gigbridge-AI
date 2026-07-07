from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., description="The user question to ask")
    history: List[Dict[str, str]] = Field(default=[], description="The conversation history so far")
    collection_name: str = Field(default="docs", description="The Chroma DB collection to query")
    style: str = Field(default="precision", description="The QA style/mode to use. E.g., 'precision' or 'fast'.")

class SourceDoc(BaseModel):
    page_content: str = Field(..., description="The chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Metadata associated with the source document")

class QueryResponse(BaseModel):
    success: bool = Field(default=True)
    answer: str = Field(..., description="The generated response from the LLM")
    context: List[SourceDoc] = Field(..., description="The list of retrieved and reranked context documents")

class IngestRequest(BaseModel):
    directory_path: Optional[str] = Field(default=None, description="Path to folder containing documents to ingest. Defaults to knowledge-base folder.")
    collection_name: str = Field(default="docs", description="The Chroma DB collection name to ingest to")

class IngestResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., description="Status message of ingestion")
    count: int = Field(..., description="Number of document chunks added")
