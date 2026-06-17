from typing import List, Optional
from pydantic import BaseModel, Field



class CategoryOption(BaseModel):
    categories_id: str = Field(
        ..., 
        description="The unique Guid identifier of the category from the database."
    )
    name: str = Field(
        ..., 
        description="The display name of the category."
    )
    is_active: bool = Field(
        default=True,
        description="Indicates whether the category is active. Inactive categories should be excluded from selection."
    )
    parent_category_id: Optional[str] = Field(
        default=None,
        description="The Guid ID of the parent category, if any."
    )

class JobPostGenerationRequest(BaseModel):
    client_questions: List[str] = Field(
        default=[],
        description="A list of questions designed to verify whether the candidate understands the job requirements."
    )
    allowed_categories: List[CategoryOption] = Field(
        ...,
        description="A required list of valid database-backed job categories to choose from."
    )

class JobPostGenerationResponse(BaseModel):
    title: str = Field(..., description="The job title")
    major: str = Field(..., description="The major or field of the job")
    category_id: str = Field(..., description="The Guid ID of the chosen category matching allowed_categories.")
    category_name: str = Field(..., description="The name of the chosen category matching allowed_categories.")
    skills : List[str] = Field(..., description="A list of required skills for the job")
    description: str = Field(..., description="Generated job description in markdown format")
    is_ai_generated: bool = Field(default=True, description="Indicates the description was AI-generated")
