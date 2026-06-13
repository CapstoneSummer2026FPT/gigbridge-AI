from fastapi import APIRouter, Depends, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.job_posts import JobPostGenerationRequest, JobPostGenerationResponse
from app.services.job_posts import JobPostService, get_job_post_service

router = APIRouter(prefix="/job-posts")

@router.post(
    "/generate",
    response_model=StandardResponse[JobPostGenerationResponse],
    status_code=status.HTTP_200_OK
)
async def generate_job_post(
    request: JobPostGenerationRequest,
    service: JobPostService = Depends(get_job_post_service)
):
    """
    Generate an AI-assisted, markdown-formatted job description.
    """
    data = await service.generate_job_description(request)
    return StandardResponse(
        success=True,
        message="Job description successfully generated.",
        data=data,
        errors=[]
    )
