import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.schemas.matching import (
    TalentRerankJob,
    TalentRerankCandidate,
    TalentRerankRequest,
    TalentRerankResponse,
    TalentRerankMatch
)
from app.services.matching import MatchingService

def test_rerank_talent_calculates_50_point_semantic_score():
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value='{"context_score": 18.0, "match_reasons": ["Strong C# experience"], "skills_matched": ["C#", "ASP.NET Core"], "skills_missing": ["Docker"]}')
    
    mock_rag = MagicMock()
    mock_memory = MagicMock()
    
    service = MatchingService(llm_gateway=mock_llm, rag_service=mock_rag, memory_manager=mock_memory)
    
    request = TalentRerankRequest(
        job=TalentRerankJob(
            job_id="job_01",
            title="Senior Backend Engineer",
            description="Looking for C# and ASP.NET Core developer",
            skills=["C#", "ASP.NET Core", "Docker"]
        ),
        candidates=[
            TalentRerankCandidate(
                freelancer_id="free_01",
                title="Senior C# Developer",
                bio="6 years experience with C# and ASP.NET Core.",
                skills=["C#", "ASP.NET Core", "PostgreSQL"],
                work_history=["Senior Engineer at Tech Corp"],
                deterministic_score=40.0
            )
        ],
        top_k=5
    )
    
    response = asyncio.run(service.rerank_talent(request))
    
    assert isinstance(response, TalentRerankResponse)
    assert len(response.matches) == 1
    
    match = response.matches[0]
    assert match.freelancer_id == "free_01"
    # Skill score: 2 matched out of 3 = 20 pts out of 30 pts.
    # Context score: 18.0 pts out of 20 pts.
    # Total semantic: 38.0 / 50.0 = 0.76
    assert match.semantic_score == 0.76
    assert "C#" in match.skills_matched
    assert "Strong C# experience" in match.match_reasons
