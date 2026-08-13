from fastapi import APIRouter, Depends, HTTPException, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.matching import (
    JobRerankRequest,
    JobRerankResponse,
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
    status_code=status.HTTP_200_OK,
    deprecated=True,
)
async def recommend_talent(
    request: TalentMatchingRequest,
    service: MatchingService = Depends(get_matching_service)
):
    del request, service
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Use /matching/rerank with a backend-authorized candidate pool.",
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
    Retrieve and deterministically rerank a backend-authorized candidate pool.
    """
    data = await service.rerank_talent(request)
    return StandardResponse(
        success=True,
        message="Talent reranking complete.",
        data=data,
        errors=[]
    )


@router.post(
    "/rerank",
    response_model=StandardResponse[TalentRerankResponse],
    status_code=status.HTTP_200_OK,
)
async def rerank_talent(
    request: TalentRerankRequest,
    service: MatchingService = Depends(get_matching_service),
):
    """Score and rank a backend-provided candidate pool."""
    data = await service.rerank_talent(request)
    return StandardResponse(
        success=True,
        message="Talent reranking complete.",
        data=data,
        errors=[],
    )


@router.post(
    "/browse-jobs",
    response_model=StandardResponse[JobRerankResponse],
    status_code=status.HTTP_200_OK,
)
async def rerank_jobs_for_freelancer(
    request: JobRerankRequest,
    service: MatchingService = Depends(get_matching_service),
):
    """Score and rank a backend-provided pool of open job posts against a freelancer profile."""
    data = await service.rerank_jobs_for_freelancer(request)
    return StandardResponse(
        success=True,
        message="Job reranking complete.",
        data=data,
        errors=[],
    )
