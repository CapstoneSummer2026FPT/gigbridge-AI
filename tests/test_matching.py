import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.api.schemas.matching import (
    TalentRerankCandidate,
    TalentRerankJob,
    TalentRerankRequest,
)
from app.core.exceptions import RAGException
from app.services.matching import MatchingService


class FakeChroma:
    def __init__(self):
        self.items = {}
        self.distance_by_candidate = {}
        self.force_outsider = False

    def get_documents(self, collection_name, ids):
        del collection_name
        if self.force_outsider:
            return {
                "ids": ["freelancer:outsider", "freelancer:profile-01"],
                "documents": ["outsider doc", "profile-01 doc"],
                "metadatas": [
                    {"freelancer_id": "outsider"},
                    {"freelancer_id": "profile-01"},
                ],
                "embeddings": [[0.1, 0.2], [0.9, 0.0]],
            }
        found = [(item_id, self.items[item_id]) for item_id in ids if item_id in self.items]
        return {
            "ids": [item_id for item_id, _ in found],
            "documents": [value[0] for _, value in found],
            "metadatas": [value[1] for _, value in found],
            "embeddings": [value[2] for _, value in found],
        }

    def upsert_documents(self, collection_name, ids, embeddings, documents, metadatas):
        del collection_name
        for item_id, emb, document, metadata in zip(ids, embeddings, documents, metadatas):
            self.items[item_id] = (document, metadata, emb)

    def query_documents(self, collection_name, query_embeddings, n_results, where):
        return {"ids": [[]], "metadatas": [[]], "distances": [[]]}


def build_request() -> TalentRerankRequest:
    return TalentRerankRequest(
        job=TalentRerankJob(
            job_id="job-01",
            title="Backend Engineer",
            description="Build C# APIs and PostgreSQL services.",
            major_name="Software Engineering",
            category_name="Backend Development",
            skills=["C#", "PostgreSQL"],
        ),
        candidates=[
            TalentRerankCandidate(
                freelancer_id="profile-01",
                title="C# API Developer",
                bio="Builds backend services with PostgreSQL.",
                availability=0,
                major_name="Software Engineering",
                categories=["Backend Development"],
                skills=["C#", "PostgreSQL"],
                verified_work=[],
            ),
            TalentRerankCandidate(
                freelancer_id="profile-02",
                title="Backend Developer",
                bio="API developer learning database systems.",
                availability=1,
                categories=["Backend Development"],
                skills=[],
                verified_work=[],
            ),
        ],
        top_k=2,
    )


def make_service(chroma=None):
    rag = MagicMock()
    def mock_get_embeddings(texts, **kwargs):
        vectors = []
        for text in texts:
            if text.startswith("Job requirements"):
                vectors.append([1.0, 0.0])
            elif text.startswith("Talent profile"):
                if "C# API Developer" in text:
                    vectors.append([0.9, 0.4358898943540674])
                elif "Backend Developer" in text:
                    vectors.append([0.65, 0.7599342076785332])
                else:
                    vectors.append([0.1, 0.2])
            else:
                vectors.append([0.1, 0.2])
        return vectors
    rag.get_embeddings = AsyncMock(side_effect=mock_get_embeddings)
    return MatchingService(
        rag_service=rag,
        chroma_client=chroma or FakeChroma(),
    ), rag


def test_rerank_uses_chroma_and_deterministic_algorithm_without_excluding_no_skill_profile():
    chroma = FakeChroma()
    chroma.distance_by_candidate = {"profile-01": 0.1, "profile-02": 0.35}
    service, rag = make_service(chroma)

    response = asyncio.run(service.rerank_talent(build_request()))

    assert [match.freelancer_id for match in response.matches] == ["profile-01", "profile-02"]
    assert response.matches[0].embedding_score == 90
    assert response.matches[0].algorithm_score > response.matches[1].algorithm_score
    assert response.matches[1].algorithm_score > 0
    assert response.scoring_version == "weighted-features-v1"
    assert all(call.kwargs["allow_fallback"] is False for call in rag.get_embeddings.await_args_list)

    # A second identical request reuses profile vectors, embeds only the job, and is reproducible.
    second_response = asyncio.run(service.rerank_talent(build_request()))
    assert rag.get_embeddings.await_count == 3
    assert second_response.matches == response.matches


def test_chroma_result_outside_backend_eligible_ids_is_rejected():
    chroma = FakeChroma()
    chroma.force_outsider = True
    service, _ = make_service(chroma)

    with pytest.raises(RAGException, match="unknown or duplicate"):
        asyncio.run(service.rerank_talent(build_request()))


def test_matching_rejects_a_mismatched_scoring_version():
    request = build_request().model_copy(update={"scoring_version": "unknown-v9"})
    service, _ = make_service()

    with pytest.raises(RAGException, match="scoring version"):
        asyncio.run(service.rerank_talent(request))


def test_candidate_contract_rejects_protected_or_identity_fields():
    with pytest.raises(ValidationError):
        TalentRerankCandidate.model_validate(
            {
                "freelancer_id": "profile-01",
                "title": "Backend Engineer",
                "availability": 0,
                "email": "private@example.com",
                "full_name": "Private Person",
            }
        )
