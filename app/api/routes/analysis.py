from fastapi import APIRouter, Depends, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis import AnalysisService, get_analysis_service

router = APIRouter(prefix="/analysis")

@router.post(
    "",
    response_model=StandardResponse[AnalysisResponse],
    status_code=status.HTTP_200_OK
)
async def perform_analysis(
    request: AnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service)
):
    """
    Perform AI audits and reports (e.g. dispute resolution, milestone status checks).
    """
    data = await service.analyze_task(request)
    return StandardResponse(
        success=True,
        message="AI Analysis complete.",
        data=data,
        errors=[]
    )
