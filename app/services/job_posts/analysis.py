"""
PURPOSE: AI task analysis service for dispute resolution, milestone status audits, and portfolio reviews.
IMPORTANCE: High — Coordinates structured AI audits and risk assessment reports for platform administration.
READING FLOW: app/schemas/analysis.py -> app/services/job_posts/analysis.py -> app/api/routes/analysis.py
"""

import json
import logging
from typing import List
from pydantic import BaseModel, Field

from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.clients.llm.gateway import LLMGateway, get_llm_gateway

logger = logging.getLogger("ai_server.analysis_service")


class AuditResult(BaseModel):
    """Pydantic schema for structured LLM audit output."""
    analysis_summary: str = Field(..., description="Markdown formatted analysis report summary")
    risk_assessment: str = Field(..., description="Assessed risk level: 'low', 'medium', or 'high'")
    key_recommendations: List[str] = Field(..., description="Actionable recommendations")
    confidence_score: float = Field(..., description="Reliability score between 0.0 and 1.0")


class AnalysisService:
    """Service coordinates structured AI audit and reports (disputes, milestone deliverables)."""

    def __init__(self, llm_gateway: LLMGateway = get_llm_gateway()):
        """Initialize AnalysisService with LLM gateway."""
        self.llm = llm_gateway

    async def analyze_task(self, request: AnalysisRequest) -> AnalysisResponse:
        """Perform AI audit and risk assessment over input context payload.
        
        Flow:
        1. Format system prompt specifying admin auditor role.
        2. Format user prompt with JSON context data payload.
        3. Invoke LLM generation with AuditResult schema.
        4. Parse returned JSON into AnalysisResponse model.
        """
        logger.info(f"Performing analysis task for type: {request.task_type}")

        system_prompt = (
            "You are an AI Analyst representing the GigBridge platform administration.\n"
            "You audit transaction payloads, milestones, and dispute logs, providing clear assessments.\n"
            "Output ONLY a JSON object matching this schema:\n"
            "{\n"
            '  "analysis_summary": "Markdown summary report...",\n'
            '  "risk_assessment": "low",\n'
            '  "key_recommendations": ["Recommendation 1", "Recommendation 2"],\n'
            '  "confidence_score": 0.95\n'
            "}"
        )

        user_prompt = (
            f"Task Category: {request.task_type}\n"
            f"Context Data Payload (JSON):\n"
            f"{json.dumps(request.context_data, indent=2)}\n\n"
        )
        if request.user_query:
            user_prompt += f"Specific Analysis Focus: {request.user_query}\n"

        try:
            response_json = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=AuditResult
            )

            data = json.loads(response_json) if isinstance(response_json, str) else response_json
            return AnalysisResponse(
                analysis_summary=data.get("analysis_summary", "Analysis completed."),
                risk_assessment=data.get("risk_assessment", "low"),
                key_recommendations=data.get("key_recommendations", []),
                confidence_score=data.get("confidence_score", 0.5)
            )
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return AnalysisResponse(
                analysis_summary=f"Analysis execution encountered an error: {str(e)}",
                risk_assessment="high",
                key_recommendations=["Retry task execution", "Verify data payload format"],
                confidence_score=0.0
            )


def get_analysis_service() -> AnalysisService:
    """Dependency injection helper returning instance of AnalysisService."""
    return AnalysisService()
