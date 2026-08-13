import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.schemas.matching import (
    TalentRerankCandidate,
    TalentRerankJob,
    TalentRerankRequest,
)
from app.core.config import Settings, settings
from app.core.exceptions import RAGException
from app.services.matching import MatchingService
from app.services.rag import RAGService


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response, calls, **kwargs):
        self.response = response
        self.calls = calls
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.calls.append((url, json, self.kwargs))
        return self.response


class _FakeChroma:
    def __init__(self):
        self.items = {}

    def get_documents(self, collection_name, ids):
        del collection_name
        found = [
            (item_id, self.items[item_id])
            for item_id in ids
            if item_id in self.items
        ]
        return {
            "ids": [item_id for item_id, _ in found],
            "metadatas": [value[0] for _, value in found],
            "embeddings": [value[1] for _, value in found],
        }

    def upsert_documents(
        self, collection_name, ids, embeddings, documents, metadatas
    ):
        del collection_name, documents
        for item_id, emb, metadata in zip(ids, embeddings, metadatas):
            self.items[item_id] = (metadata, emb)

    def query_documents(
        self, collection_name, query_embeddings, n_results, where
    ):
        return {"ids": [[]], "metadatas": [[]], "distances": [[]]}


class OllamaEmbeddingTests(unittest.TestCase):
    def _service(self):
        return RAGService(chroma_client=MagicMock(), llm_gateway=MagicMock())

    def test_matching_configuration_accepts_ollama(self):
        configured = Settings(
            APP_ENV="test",
            AI_SERVER_API_KEY="dev-key-please-change-in-env",
            MATCHING_EMBEDDING_PROVIDER="ollama",
            MATCHING_EMBEDDING_MODEL="embeddinggemma",
            _env_file=None,
        )
        self.assertEqual(configured.MATCHING_EMBEDDING_PROVIDER, "ollama")

    def test_matching_service_routes_profile_and_job_embeddings_to_ollama(self):
        rag = MagicMock()
        rag.get_embeddings = AsyncMock(
            side_effect=lambda texts, **kwargs: [[0.1, 0.2] for _ in texts]
        )
        service = MatchingService(rag_service=rag, chroma_client=_FakeChroma())
        request = TalentRerankRequest(
            job=TalentRerankJob(job_id="job-1", title="Backend Engineer"),
            candidates=[
                TalentRerankCandidate(
                    freelancer_id="profile-1",
                    title="API Developer",
                    availability=0,
                )
            ],
            top_k=1,
        )

        with (
            patch.object(settings, "MATCHING_EMBEDDING_PROVIDER", "ollama"),
            patch.object(settings, "MATCHING_EMBEDDING_MODEL", "embeddinggemma"),
        ):
            response = asyncio.run(service.rerank_talent(request))

        self.assertEqual(response.embedding_model, "ollama:embeddinggemma")
        self.assertEqual(rag.get_embeddings.await_count, 2)
        for call in rag.get_embeddings.await_args_list:
            self.assertEqual(call.kwargs["provider"], "ollama")
            self.assertEqual(call.kwargs["model"], "embeddinggemma")
            self.assertFalse(call.kwargs["allow_fallback"])

    def test_ollama_embeddings_use_native_batch_endpoint(self):
        calls = []
        response = _FakeResponse({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

        def client_factory(**kwargs):
            return _FakeAsyncClient(response, calls, **kwargs)

        with (
            patch("app.services.rag.httpx.AsyncClient", side_effect=client_factory),
            patch.object(settings, "LOCAL_OLLAMA_URL", "http://127.0.0.1:11434/"),
        ):
            vectors = asyncio.run(
                self._service().get_embeddings(
                    ["profile", "job"],
                    provider="ollama",
                    model="embeddinggemma",
                    allow_fallback=False,
                )
            )

        self.assertEqual(vectors, [[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(len(calls), 1)
        url, payload, client_kwargs = calls[0]
        self.assertEqual(url, "http://127.0.0.1:11434/api/embed")
        self.assertEqual(
            payload,
            {
                "model": "embeddinggemma",
                "input": ["profile", "job"],
                "truncate": True,
            },
        )
        self.assertEqual(client_kwargs["timeout"], 120.0)

    def test_ollama_incomplete_batch_is_rejected(self):
        response = _FakeResponse({"embeddings": [[0.1, 0.2]]})

        def client_factory(**kwargs):
            return _FakeAsyncClient(response, [], **kwargs)

        with patch(
            "app.services.rag.httpx.AsyncClient", side_effect=client_factory
        ):
            with self.assertRaisesRegex(RAGException, "incomplete embedding batch"):
                asyncio.run(
                    self._service().get_embeddings(
                        ["profile", "job"],
                        provider="ollama",
                        model="embeddinggemma",
                        allow_fallback=False,
                    )
                )

    def test_ollama_non_object_response_is_rejected(self):
        response = _FakeResponse([[0.1, 0.2]])

        def client_factory(**kwargs):
            return _FakeAsyncClient(response, [], **kwargs)

        with patch(
            "app.services.rag.httpx.AsyncClient", side_effect=client_factory
        ):
            with self.assertRaisesRegex(RAGException, "invalid embedding response"):
                asyncio.run(
                    self._service().get_embeddings(
                        ["profile"],
                        provider="ollama",
                        model="embeddinggemma",
                        allow_fallback=False,
                    )
                )


if __name__ == "__main__":
    unittest.main()
