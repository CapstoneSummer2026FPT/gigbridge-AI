from fastapi import APIRouter, Depends, status
from app.api.schemas.base import StandardResponse
from app.api.schemas.job_posts import (
    JobPostGenerationRequest, JobPostGenerationResponse,
    JobPostDetailsGenerationResponse,
    JobPostHiringPlanGenerationRequest, JobPostHiringPlanGenerationResponse
)
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

@router.post(
    "/generate/details",
    response_model=StandardResponse[JobPostDetailsGenerationResponse],
    status_code=status.HTTP_200_OK
)
async def generate_job_post_details(
    request: JobPostGenerationRequest,
    service: JobPostService = Depends(get_job_post_service)
):
    """
    Generate job details (Title, Major, Category, Skills, Description).
    """
    data = await service.generate_job_details(request)
    return StandardResponse(
        success=True,
        message="Job details successfully generated.",
        data=data,
        errors=[]
    )

@router.post(
    "/generate/hiring-plan",
    response_model=StandardResponse[JobPostHiringPlanGenerationResponse],
    status_code=status.HTTP_200_OK
)
async def generate_job_post_hiring_plan(
    request: JobPostHiringPlanGenerationRequest,
    service: JobPostService = Depends(get_job_post_service)
):
    """
    Generate job hiring plan (Vetting Questions, Milestones).
    """
    data = await service.generate_job_hiring_plan(request)
    return StandardResponse(
        success=True,
        message="Job hiring plan successfully generated.",
        data=data,
        errors=[]
    )
