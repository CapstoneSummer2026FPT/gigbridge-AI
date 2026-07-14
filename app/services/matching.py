import json
import logging
from typing import List, Dict, Any, Optional
from app.api.schemas.matching import TalentMatchingRequest, TalentMatchingResponse, TalentMatchResult
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.rag import RAGService, get_rag_service
from app.services.memory import MemoryManager, get_memory_manager

logger = logging.getLogger("ai_server.matching_service")

class MatchingService:
    """Service coordinates semantic matching between job openings and freelancer candidate profiles"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        rag_service: RAGService = get_rag_service(),
        memory_manager: MemoryManager = get_memory_manager()
    ):
        self.llm = llm_gateway
        self.rag = rag_service
        self.memory = memory_manager
        self.collection_name = "ai-candidate-matching"

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
