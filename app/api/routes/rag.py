from fastapi import APIRouter, Depends, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.rag import QueryRequest, QueryResponse, IngestRequest, IngestResponse
from app.services.rag import RAGService, get_rag_service

router = APIRouter(prefix="/rag")

@router.post(
    "/query",
    response_model=StandardResponse[QueryResponse],
    status_code=status.HTTP_200_OK
)
async def query_rag(
    request: QueryRequest,
    service: RAGService = Depends(get_rag_service)
):
    """
    Perform a RAG query to search the knowledge base and return a synthesized response.
    """
    answer, context = await service.answer_question(
        question=request.question,
        history=request.history,
        collection_name=request.collection_name
    )
    source_docs = [
        {"page_content": doc.page_content, "metadata": doc.metadata}
        for doc in context
    ]
    data = QueryResponse(
        success=True,
        answer=answer,
        context=source_docs
    )
    return StandardResponse(
        success=True,
        message="RAG query completed successfully.",
        data=data,
        errors=[]
    )

@router.post(
    "/ingest",
    response_model=StandardResponse[IngestResponse],
    status_code=status.HTTP_200_OK
)
async def ingest_rag(
    request: IngestRequest,
    service: RAGService = Depends(get_rag_service)
):
    """
    Ingest documents from a directory into the Chroma DB collection.
    """
    count = await service.ingest_documents(
        directory_path=request.directory_path,
        collection_name=request.collection_name
    )
    data = IngestResponse(
        success=True,
        message="Ingestion completed successfully.",
        count=count
    )
    return StandardResponse(
        success=True,
        message="RAG ingestion completed successfully.",
        data=data,
        errors=[]
    )
