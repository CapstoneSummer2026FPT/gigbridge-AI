"""
PURPOSE: Pydantic data models for AI task analysis, dispute resolution, and risk assessments.
IMPORTANCE: High — Defines API contracts for job and task analysis endpoints.
READING FLOW: app/schemas/analysis.py -> app/services/job_posts/analysis.py -> app/api/routes/analysis.py
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AnalysisRequest(BaseModel):
    task_type: str = Field(..., description="Type of analysis: 'dispute_resolution', 'milestone_status', or 'portfolio_review'")
    context_data: Dict[str, Any] = Field(..., description="Arbitrary JSON payload containing task details (e.g. dispute message transcripts)")
    user_query: Optional[str] = Field(default=None, description="Specific question or override for the analysis")

class AnalysisResponse(BaseModel):
    analysis_summary: str = Field(..., description="Markdown formatted analysis report")
    risk_assessment: str = Field(..., description="Assessed risk level: 'low', 'medium', or 'high'")
    key_recommendations: List[str] = Field(..., description="List of actionable recommendations")
    confidence_score: float = Field(..., description="Reliability score of generated analysis (0.0 to 1.0)")
