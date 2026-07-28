import json
import logging
import math
import re
from typing import List, Dict, Any, Optional
from app.api.schemas.matching import (
    TalentMatchingRequest,
    TalentMatchingResponse,
    TalentMatchResult,
    TalentRerankCandidate,
    TalentRerankJob,
    TalentRerankMatch,
    TalentRerankRequest,
    TalentRerankResponse,
)
from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.core.config import settings
from app.services.rag import RAGService, get_rag_service
from app.services.memory import MemoryManager, get_memory_manager

logger = logging.getLogger("ai_server.matching_service")

class MatchingService:
    """Service coordinates semantic matching between job openings and freelancer candidate profiles"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        rag_service: RAGService = get_rag_service(),
        memory_manager: MemoryManager = get_memory_manager(),
        chroma_client: ChromaDBClient = get_chroma_client(),
    ):
        self.llm = llm_gateway
        self.rag = rag_service
        self.memory = memory_manager
        self.chroma = chroma_client
        self.collection_name = "ai-candidate-matching"

    async def rerank_talent(
        self, request: TalentRerankRequest
    ) -> TalentRerankResponse:
        """Rerank the authoritative candidate pool supplied by the backend."""
        provider = settings.MATCHING_EMBEDDING_PROVIDER
        model = settings.MATCHING_EMBEDDING_MODEL
        candidate_texts = [
            self._candidate_text(candidate) for candidate in request.candidates
        ]
        candidate_vectors = await self.rag.get_embeddings(
            candidate_texts,
            provider=provider,
            model=model,
            allow_fallback=False,
        )
        job_vector = (
            await self.rag.get_embeddings(
                [self._job_text(request.job)],
                provider=provider,
                model=model,
                allow_fallback=False,
            )
        )[0]

        matches = []
        for candidate, vector in zip(request.candidates, candidate_vectors):
            embedding_score = round(
                max(0.0, min(100.0, self._cosine(job_vector, vector) * 100.0)),
                2,
            )
            algorithm_score, reasons, strengths = self._algorithm_score(
                request.job, candidate
            )
            matches.append(
                TalentRerankMatch(
                    freelancer_id=candidate.freelancer_id,
                    embedding_score=embedding_score,
                    algorithm_score=algorithm_score,
                    match_reasons=reasons,
                    semantic_strengths=strengths,
                )
            )

        matches.sort(
            key=lambda item: (
                -(0.6 * item.embedding_score + 0.4 * item.algorithm_score),
                item.freelancer_id,
            )
        )
        embedding_model = f"{provider}:{model}"
        return TalentRerankResponse(
            matches=matches[: min(request.top_k, len(matches))],
            algorithm_version=request.algorithm_version,
            embedding_model=embedding_model,
            scoring_version=request.scoring_version,
        )

    @staticmethod
    def _normalise(values: List[str]) -> set[str]:
        return {value.strip().casefold() for value in values if value.strip()}

    @staticmethod
    def _tokens(value: Optional[str]) -> set[str]:
        return set(re.findall(r"[\w+#.-]+", (value or "").casefold()))

    @classmethod
    def _algorithm_score(
        cls, job: TalentRerankJob, candidate: TalentRerankCandidate
    ) -> tuple[float, List[str], List[str]]:
        required = cls._normalise(job.skills + job.custom_skills)
        candidate_skills = cls._normalise(candidate.skills)
        verified_skills = cls._normalise(
            [skill for work in candidate.verified_work for skill in work.skills]
        )
        effective_skills = candidate_skills | verified_skills
        matched = sorted(required & effective_skills)

        skill_score = 55.0 * len(matched) / len(required) if required else 0.0
        job_tokens = cls._tokens(f"{job.title} {job.description}")
        profile_tokens = cls._tokens(f"{candidate.title or ''} {candidate.bio or ''}")
        text_score = (
            25.0 * len(job_tokens & profile_tokens) / len(job_tokens)
            if job_tokens
            else 0.0
        )
        job_taxonomy = cls._normalise(
            [job.major_name or "", job.category_name or ""]
        )
        candidate_taxonomy = cls._normalise(
            [candidate.major_name or ""] + candidate.categories
        )
        taxonomy_score = 15.0 if job_taxonomy & candidate_taxonomy else 0.0
        availability_score = 5.0 if candidate.availability == 0 else (
            2.5 if candidate.availability == 1 else 0.0
        )
        score = round(
            min(100.0, skill_score + text_score + taxonomy_score + availability_score),
            2,
        )

        reasons = []
        strengths = []
        if required:
            reasons.append(f"{len(matched)}/{len(required)} requested skills matched")
        if matched:
            strengths.append(f"Skill alignment: {', '.join(matched[:5])}")
        if verified_skills & required:
            strengths.append("Relevant skills are supported by verified work")
        if taxonomy_score:
            strengths.append("Major or category aligns with the job")
        if not reasons:
            reasons.append("Candidate assessed using semantic profile similarity")
        return score, reasons[:3], strengths[:5]

    @staticmethod
    def _cosine(left: List[float], right: List[float]) -> float:
        if not left or len(left) != len(right):
            return 0.0
        denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(
            sum(x * x for x in right)
        )
        if denominator == 0:
            return 0.0
        return sum(x * y for x, y in zip(left, right)) / denominator

    @staticmethod
    def _job_text(job: TalentRerankJob) -> str:
        return " | ".join(
            filter(
                None,
                [
                    job.title,
                    job.description,
                    job.industry,
                    job.major_name,
                    job.category_name,
                    ", ".join(job.skills + job.custom_skills),
                    job.location,
                ],
            )
        )

    @staticmethod
    def _candidate_text(candidate: TalentRerankCandidate) -> str:
        work = " ".join(
            f"{item.title} {item.description or ''} "
            f"{item.major_name or ''} {item.category_name or ''} "
            f"{' '.join(item.skills)}"
            for item in candidate.verified_work
        )
        return " | ".join(
            filter(
                None,
                [
                    candidate.title,
                    candidate.bio,
                    candidate.major_name,
                    ", ".join(candidate.categories),
                    ", ".join(candidate.skills),
                    candidate.location,
                    work,
                ],
            )
        )

    async def match_talent(self, request: TalentMatchingRequest) -> TalentMatchingResponse:
        logger.info(f"Running semantic matching for job post ID: {request.job_id}")
        
        # Load job post details from cache/database
        job_details = await self.memory.get_domain_context("job_posts", request.job_id)
        if not job_details:
            # Fallback mock job post if not indexed
            job_details = {
                "title": "Senior Backend Developer",
                "category": "Web Development",
                "skills": ["C#", "ASP.NET Core", "PostgreSQL", "Docker"],
                "description": "Seeking a backend engineer specializing in C#, ASP.NET Core, database design, and CI/CD pipelines."
            }

        # Query vector database for candidate resumes/profiles
        search_query = f"{job_details['title']}. Required skills: {', '.join(job_details['skills'])}"
        candidates = await self.rag.retrieve_context(
            collection_name=self.collection_name,
            query=search_query,
            top_k=request.top_k * 2  # Retrieve more than requested to allow filtering/rerank
        )

        # Mocking candidates indexing if vector DB is empty (first run fallback)
        if not candidates:
            logger.info("Vector store empty. Injecting mock developer profiles for matching demonstration.")
            mock_resumes = [
                ("freelancer_01", "Nguyễn Văn Trí", "Senior Backend Developer", "ASP.NET Core, PostgreSQL, Docker, AWS, microservices design. 6 years experience."),
                ("freelancer_02", "Trần Quốc Bảo", "Flutter Mobile App Developer", "Flutter, React Native, Dart, REST APIs, clean architecture. 3 years experience."),
                ("freelancer_03", "Ngô Phương Thảo", "Smart Contract Engineer", "Solidity, Ethereum, Web3.js, Rust, security audits. 4 years experience."),
                ("freelancer_04", "Lê Thị Hoa", "Frontend React Developer", "React, TypeScript, Redux, Tailwind CSS, performance tuning. 4 years experience.")
            ]
            for fid, name, title, resume in mock_resumes:
                await self.rag.add_documents(
                    collection_name=self.collection_name,
                    text=f"Name: {name}\nTitle: {title}\nResume: {resume}",
                    metadata={"freelancer_id": fid, "full_name": name, "title": title}
                )
            # Query again after indexing
            candidates = await self.rag.retrieve_context(collection_name=self.collection_name, query=search_query, top_k=request.top_k)

        # Rerank and evaluate alignment for each candidate
        matches = []
        for doc in candidates:
            # Try parsing metadata, fallback to extracting from page_content text
            freelancer_id = doc["metadata"].get("freelancer_id")
            full_name = doc["metadata"].get("full_name")
            candidate_title = doc["metadata"].get("title")

            if not full_name or not freelancer_id:
                import re
                text = doc["page_content"]
                
                # Find Name/Candidate
                name_match = re.search(r"(?:Candidate|Name):\s*([^\n\-\*#]+)", text, re.IGNORECASE)
                if name_match:
                    full_name = name_match.group(1).strip()
                else:
                    full_name = "Unknown Freelancer"
                
                # Find Role/Title
                role_match = re.search(r"(?:Role|Title|Position):\s*([^\n\-\*#]+)", text, re.IGNORECASE)
                if role_match:
                    candidate_title = role_match.group(1).strip()
                else:
                    candidate_title = "Developer"

                # Generate pseudo ID
                if not freelancer_id:
                    clean_name = "".join(c for c in full_name if c.isalnum() or c.isspace())
                    freelancer_id = f"freelancer_{clean_name.lower().replace(' ', '_')}"
            
            if not candidate_title:
                candidate_title = "Developer"
            
            # Formulate prompt for LLM profile match scoring
            system_prompt = (
                "You are an expert talent recruitment assistant.\n"
                "Evaluate how well a freelancer's resume matches the job requirements.\n"
                "Output ONLY a JSON object matching this schema:\n"
                "{\n"
                '  "match_score": 0.85,\n'
                '  "match_reasons": ["6 years experience with ASP.NET Core matching requirements"],\n'
                '  "skills_matched": ["ASP.NET Core", "Docker"],\n'
                '  "skills_missing": ["PostgreSQL"]\n'
                "}"
            )
            
            user_prompt = (
                f"Job Requirements:\n"
                f"- Title: {job_details['title']}\n"
                f"- Description: {job_details['description']}\n"
                f"- Required Skills: {', '.join(job_details['skills'])}\n\n"
                f"Freelancer Resume:\n"
                f"{doc['page_content']}"
            )

            try:
                # Structuring the response model
                from pydantic import BaseModel, Field
                class MatchEvaluation(BaseModel):
                    match_score: float = Field(..., description="Match alignment score between 0.0 and 1.0")
                    match_reasons: List[str] = Field(..., description="Actionable reasons for the match decision")
                    skills_matched: List[str] = Field(..., description="Skills matching requirements")
                    skills_missing: List[str] = Field(..., description="Missing skills requested by client")

                eval_json = await self.llm.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format=MatchEvaluation
                )
                
                eval_data = json.loads(eval_json)
                
                matches.append(TalentMatchResult(
                    freelancer_id=freelancer_id,
                    full_name=full_name,
                    title=candidate_title,
                    match_score=eval_data.get("match_score", 0.5),
                    match_reasons=eval_data.get("match_reasons", []),
                    skills_matched=eval_data.get("skills_matched", []),
                    skills_missing=eval_data.get("skills_missing", [])
                ))
            except Exception as e:
                logger.error(f"Error evaluating match for candidate {full_name}: {str(e)}")
                # Simple fallback match item
                matches.append(TalentMatchResult(
                    freelancer_id=freelancer_id,
                    full_name=full_name,
                    title=candidate_title,
                    match_score=0.5,
                    match_reasons=["Semantic match identified in vector store"],
                    skills_matched=[],
                    skills_missing=[]
                ))

        # Sort matches by score descending
        matches.sort(key=lambda x: x.match_score, reverse=True)
        # Apply slice limit
        final_matches = matches[:request.top_k]

        return TalentMatchingResponse(
            job_id=request.job_id,
            matches=final_matches
        )

# Dependency helper
def get_matching_service() -> MatchingService:
    return MatchingService()
