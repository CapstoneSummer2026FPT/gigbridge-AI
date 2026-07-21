from fastapi import APIRouter, Depends, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.matching import (
    TalentMatchingRequest,
    TalentMatchingResponse,
    TalentRerankRequest,
    TalentRerankResponse
)
from app.services.matching import MatchingService, get_matching_service

router = APIRouter(prefix="/matching")

@router.post(
    "/recommend",
    response_model=StandardResponse[TalentMatchingResponse],
    status_code=status.HTTP_200_OK
)
async def recommend_talent(
    request: TalentMatchingRequest,
    service: MatchingService = Depends(get_matching_service)
):
    """
    Find and rank candidates matching the requirements of a specified Job Post.
    """
    data = await service.match_talent(request)
    return StandardResponse(
        success=True,
        message="Talent recommendation complete.",
        data=data,
        errors=[]
    )

@router.post(
    "/rerank",
    response_model=StandardResponse[TalentRerankResponse],
    status_code=status.HTTP_200_OK
)
async def rerank_talent(
    request: TalentRerankRequest,
    service: MatchingService = Depends(get_matching_service)
):
    """
    Rerank a candidate shortlist against job requirements using 50-point Semantic RAG scoring.
    """
    data = await service.rerank_talent(request)
    return StandardResponse(
        success=True,
        message="Talent reranking complete.",
        data=data,
        errors=[]
    )
