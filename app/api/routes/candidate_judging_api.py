"""
PURPOSE: FastAPI routes for AI Candidate Proposal & Vetting Screening Q&A Evaluation.
IMPORTANCE: Critical — Primary entry points for .NET backend integration for single and batch proposal judging.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.base import StandardResponse
from app.schemas.candidate_judging_schemas import (
    CandidateJudgingRequest,
    CandidateJudgingResponse,
    BatchCandidateJudgingRequest,
    BatchCandidateJudgingResponse,
)
from app.services.proposals.candidate_judging_service import (
    CandidateJudgingService,
    get_candidate_judging_service,
)

router = APIRouter(prefix="/eval", tags=["Candidate Evaluation Engine"])
logger = logging.getLogger("ai_server.candidate_judging_api")


@router.post(
    "/candidate-judging",
    response_model=StandardResponse[CandidateJudgingResponse],
    status_code=status.HTTP_200_OK,
)
async def evaluate_candidate(
    payload: CandidateJudgingRequest,
    service: CandidateJudgingService = Depends(get_candidate_judging_service),
):
    """Evaluate a single candidate proposal and screening Q&A answers against job post baseline."""
    try:
        data = await service.evaluate_candidate(payload)
        return StandardResponse(
            success=True,
            message="Candidate proposal successfully evaluated.",
            data=data,
            errors=[],
        )
    except Exception as exc:
        logger.exception("Failed to evaluate candidate proposal", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail={"code": "candidate_eval_failed", "message": str(exc)},
        )


@router.post(
    "/candidate-judging/batch",
    response_model=StandardResponse[BatchCandidateJudgingResponse],
    status_code=status.HTTP_200_OK,
)
async def evaluate_candidate_batch(
    payload: BatchCandidateJudgingRequest,
    service: CandidateJudgingService = Depends(get_candidate_judging_service),
):
    """Evaluate a batch of candidate proposals in chunked parallel executions."""
    try:
        data = await service.evaluate_batch(payload)
        return StandardResponse(
            success=True,
            message="Batch candidate proposals successfully evaluated.",
            data=data,
            errors=[],
        )
    except Exception as exc:
        logger.exception("Failed batch candidate proposal evaluation", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail={"code": "batch_candidate_eval_failed", "message": str(exc)},
        )
