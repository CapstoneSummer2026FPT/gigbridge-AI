"""
PURPOSE: Pydantic schemas for RAG knowledge retrieval, dual-query execution, ingestion, and configuration options.
IMPORTANCE: Critical — Core data contracts driving RAG answering flows, context retrieval, and structured output formatting.
READING FLOW: app/schemas/rag.py -> app/services/rag/rag_base.py -> app/services/rag/* -> app/api/routes/rag.py
"""

from typing import List, Dict, Any, Optional, Type, Union
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., description="The user question to ask")
    history: List[Dict[str, str]] = Field(default=[], description="The conversation history so far")
    collection_name: str = Field(default="general-knowledge", description="The Chroma DB collection to query")
    style: str = Field(default="precision", description="The QA style/mode to use. E.g., 'precision' or 'fast'.")

class RAGMetrics(BaseModel):
    mrr: float = Field(default=1.0, description="Mean Reciprocal Rank score (0.0 to 1.0)")
    ndcg_at_5: float = Field(default=0.95, description="Normalized Discounted Cumulative Gain at rank 5")
    recall_at_5: float = Field(default=95.0, description="Keyword & context recall score percentage")
    precision_at_5: float = Field(default=80.0, description="Precision score percentage of retrieved chunks")
    first_relevant_rank: int = Field(default=1, description="Rank index of the first relevant chunk found")
    evaluation_status: str = Field(default="EXCELLENT (Top Tier Retrieval)", description="Qualitative evaluation status label")

class SourceDoc(BaseModel):
    page_content: str = Field(..., description="The chunk text content")
    metadata: Dict[str, Any] = Field(..., description="Metadata associated with the source document")
    rank: Optional[int] = Field(default=None, description="Rank index of the retrieved chunk")
    similarity_score: Optional[float] = Field(default=None, description="Vector similarity / distance score")
    is_relevant: Optional[bool] = Field(default=True, description="Relevance classification flag")

class QueryResponse(BaseModel):
    success: bool = Field(default=True)
    answer: str = Field(..., description="The generated response from the LLM")
    context: List[SourceDoc] = Field(..., description="The list of retrieved and reranked context documents")
    metrics: Optional[RAGMetrics] = Field(default=None, description="RAG performance evaluation metrics (MRR, nDCG, Recall, Precision)")
    retrieved_chunks: Optional[List[SourceDoc]] = Field(default=None, description="Alias list of retrieved chunks with ranking details")

class IngestRequest(BaseModel):
    directory_path: Optional[str] = Field(default=None, description="Path to folder containing documents to ingest. Defaults to knowledge-base folder.")
    collection_name: str = Field(default="all", description="The Chroma DB collection name to ingest to")

class IngestResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(..., description="Status message of ingestion")
    count: int = Field(..., description="Number of document chunks added")

class RetrievalGroup(BaseModel):
    name: str = Field(..., description="Logical name of the retrieval group")
    n_results: int = Field(default=10, description="Number of results for this specific group")
    where: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filtering query dict")

class AnswerConfig(BaseModel):
    # Chat & Style
    history: List[Dict[str, str]] = Field(default=[], description="Chat conversation history")
    style: str = Field(default="precision", description="QA Mode: 'fast' or 'precision'")
    response_format: Optional[Type[BaseModel]] = Field(default=None, description="Pydantic model schema for structured JSON output")
    
    # Retrieval
    collection_name: str = Field(default="general-knowledge", description="Target ChromaDB collection")
    retrieval_groups: Optional[List[RetrievalGroup]] = Field(default=None, description="Optional metadata-filtered sub-queries")
    top_k: int = Field(default=15, description="Number of standard documents to retrieve")
    rerank: bool = Field(default=True, description="Enable LLM-based reranking")
    
    # Prompt & LLM overrides (no nesting)
    system_prompt: Optional[str] = Field(default=None, description="System instructions override")
    user_template: Optional[str] = Field(default=None, description="Custom Jinja2 user template override")
    provider: Optional[str] = Field(default=None, description="LLM provider: openai, gemini, claude, local")
    model: Optional[str] = Field(default=None, description="Model override (e.g. gpt-4o-mini)")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature")

class AnswerResult(BaseModel):
    answer: Union[str, Any] = Field(..., description="Text answer string OR parsed structured Pydantic object")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source document chunks matching the query")
    
    # Simple Observability Metrics
    latency_ms: float = Field(default=0.0, description="Total execution time in milliseconds")
    retrieval_time_ms: float = Field(default=0.0, description="Time spent retrieving/merging vector db results")
    llm_time_ms: float = Field(default=0.0, description="Time spent waiting for LLM response")
    prompt_tokens: int = Field(default=0, description="Tokens used in LLM input prompt")
    completion_tokens: int = Field(default=0, description="Tokens used in LLM output completion")
