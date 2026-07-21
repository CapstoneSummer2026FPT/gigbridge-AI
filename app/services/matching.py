import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.api.schemas.matching import (
    TalentMatchingRequest,
    TalentMatchingResponse,
    TalentMatchResult,
    TalentRerankRequest,
    TalentRerankResponse,
    TalentRerankMatch
)
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.rag import RAGService, get_rag_service
from app.services.memory import MemoryManager, get_memory_manager

logger = logging.getLogger("ai_server.matching_service")

class CandidateEvaluationOutput(BaseModel):
    context_score: float = Field(..., description="Contextual domain experience fit score between 0.0 and 20.0 points")
    match_reasons: List[str] = Field(default_factory=list, description="1 to 3 concise rationale points for candidate fit")
    skills_matched: List[str] = Field(default_factory=list, description="Skills matching the job requirements")
    skills_missing: List[str] = Field(default_factory=list, description="Required job skills missing from candidate profile")

class MatchingService:
    """Service handling AI candidate reranking and talent matching using 50-point Semantic RAG scoring"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        rag_service: RAGService = get_rag_service(),
        memory_manager: MemoryManager = get_memory_manager()
    ):
        self.llm = llm_gateway
        self.rag = rag_service
        self.memory = memory_manager

    async def rerank_talent(self, request: TalentRerankRequest) -> TalentRerankResponse:
        """
        Rerank shortlist candidates using simplified 50-Point Semantic RAG evaluation:
        - Skill Overlap (0 to 30 Points): Exact matching required skills
        - GPT Context Fit (0 to 20 Points): LLM domain experience and profile evaluation
        Returns normalized semantic_score (0.0 to 1.0) along with skills & match reasoning.
        """
        logger.info(f"Reranking {len(request.candidates)} candidate(s) for job '{request.job.title}' (ID: {request.job.job_id})")
        
        job_skills = [s.strip().lower() for s in request.job.skills if s.strip()]
        matches: List[TalentRerankMatch] = []

        system_prompt = (
            "You are an expert tech recruiter for GigBridge.\n"
            "Evaluate the candidate's profile (title, bio, work history) against the job opening.\n"
            "Assign a 'context_score' between 0.0 and 20.0 representing overall domain, experience, and title alignment.\n"
            "Provide 1-3 clear, professional bullet reasons for your rating.\n"
            "List matched skills and missing skills relative to the job requirements."
        )

        for candidate in request.candidates:
            cand_skills_raw = candidate.skills or []
            cand_skills_lower = [s.strip().lower() for s in cand_skills_raw if s.strip()]

            # 1. Skill Overlap Calculation (0 to 30 Points)
            if not job_skills:
                skill_score = 30.0
                matched_skills = cand_skills_raw
                missing_skills = []
            else:
                matched_set = set()
                missing_set = set()
                for original_skill, lower_skill in zip(request.job.skills, job_skills):
                    if any(lower_skill in cs for cs in cand_skills_lower) or any(cs in lower_skill for cs in cand_skills_lower):
                        matched_set.add(original_skill)
                    else:
                        missing_set.add(original_skill)

                matched_skills = list(matched_set)
                missing_skills = list(missing_set)
                overlap_ratio = len(matched_skills) / len(request.job.skills)
                skill_score = round(overlap_ratio * 30.0, 2)

            # 2. GPT Context Fit Evaluation (0 to 20 Points)
            user_prompt = (
                f"JOB OPENING:\n"
                f"- Title: {request.job.title}\n"
                f"- Required Skills: {', '.join(request.job.skills)}\n"
                f"- Description: {request.job.description or 'N/A'}\n\n"
                f"CANDIDATE PROFILE:\n"
                f"- Freelancer ID: {candidate.freelancer_id}\n"
                f"- Title: {candidate.title or 'N/A'}\n"
                f"- Bio: {candidate.bio or 'N/A'}\n"
                f"- Skills: {', '.join(candidate.skills)}\n"
                f"- Work History: {'; '.join(candidate.work_history or [])}\n"
            )

            try:
                eval_json = await self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format=CandidateEvaluationOutput
                )
                eval_data = json.loads(eval_json)
                context_score = min(max(float(eval_data.get("context_score", 10.0)), 0.0), 20.0)
                reasons = eval_data.get("match_reasons", [])
                
                # Combine LLM skills feedback with deterministic skill overlap if present
                if not matched_skills and eval_data.get("skills_matched"):
                    matched_skills = eval_data.get("skills_matched")
                if not missing_skills and eval_data.get("skills_missing"):
                    missing_skills = eval_data.get("skills_missing")
            except Exception as e:
                logger.warning(f"Error calling LLM for candidate {candidate.freelancer_id}: {str(e)}")
                context_score = 10.0
                reasons = [f"Skill match ratio: {len(matched_skills)}/{len(request.job.skills)}"]

            total_semantic_pts = min(skill_score + context_score, 50.0)
            normalized_score = round(total_semantic_pts / 50.0, 4)

            matches.append(TalentRerankMatch(
                freelancer_id=candidate.freelancer_id,
                semantic_score=normalized_score,
                match_reasons=reasons,
                skills_matched=matched_skills,
                skills_missing=missing_skills
            ))

        # Sort matches by semantic_score descending
        matches.sort(key=lambda m: m.semantic_score, reverse=True)
        if request.top_k > 0:
            matches = matches[:request.top_k]

        return TalentRerankResponse(matches=matches)

    async def match_talent(self, request: TalentMatchingRequest) -> TalentMatchingResponse:
        """Fallback direct RAG matching when no shortlist is provided"""
        logger.info(f"Running fallback matching for job post ID: {request.job_id}")
        return TalentMatchingResponse(job_id=request.job_id, matches=[])

# Dependency helper
def get_matching_service() -> MatchingService:
    return MatchingService()
