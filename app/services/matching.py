import asyncio
import hashlib
import logging
import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence

from app.api.schemas.matching import (
    JobRerankCandidate,
    JobRerankFreelancer,
    JobRerankMatch,
    JobRerankRequest,
    JobRerankResponse,
    TalentRerankCandidate,
    TalentRerankJob,
    TalentRerankMatch,
    TalentRerankRequest,
    TalentRerankResponse,
)
from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.core.config import settings
from app.core.exceptions import RAGException
from app.services.rag import RAGService, get_rag_service

logger = logging.getLogger("ai_server.matching_service")

_TOKEN_PATTERN = re.compile(r"[a-z0-9+#.]{2,}")
_STOP_WORDS = {
    "and", "are", "for", "from", "into", "that", "the", "this", "with",
    "will", "your", "you", "our", "job", "work", "role", "using", "have",
    "has", "build", "developer", "engineer",
}


class MatchingService:
    """Embedding retrieval followed by deterministic weighted feature reranking."""

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        chroma_client: Optional[ChromaDBClient] = None,
    ):
        self.rag = rag_service or get_rag_service()
        self.chroma = chroma_client or get_chroma_client()

    async def rerank_talent(self, request: TalentRerankRequest) -> TalentRerankResponse:
        self._validate_request_versions(request)
        candidates_by_id = self._candidate_map(request.candidates)
        if not candidates_by_id:
            return self._response([])

        documents = {
            candidate_id: self._profile_document(candidate)
            for candidate_id, candidate in candidates_by_id.items()
        }
        collection_name = self._collection_name()
        await self._upsert_changed_profiles(collection_name, documents)
        retrieved = await self._retrieve(
            collection_name,
            request.job,
            list(candidates_by_id),
        )

        rerank_limit = min(settings.MATCHING_RERANK_LIMIT, len(retrieved))
        rerank_ids = [candidate_id for candidate_id, _ in retrieved[:rerank_limit]]
        algorithm_scores = self._evaluate_algorithm(
            request.job,
            rerank_ids,
            candidates_by_id,
        )

        embedding_scores = dict(retrieved)
        matches = [
            TalentRerankMatch(
                freelancer_id=candidate_id,
                embedding_score=embedding_scores[candidate_id],
                algorithm_score=evaluation[0],
                semantic_strengths=evaluation[1],
                match_reasons=evaluation[2],
            )
            for candidate_id, evaluation in algorithm_scores.items()
        ]
        # 45:35 is renormalized here because backend evidence is added after this service.
        matches.sort(
            key=lambda match: (
                -(0.5625 * match.embedding_score + 0.4375 * match.algorithm_score),
                match.freelancer_id,
            )
        )
        expected = min(request.top_k, len(candidates_by_id), rerank_limit)
        matches = matches[:expected]
        if len(matches) != expected:
            raise RAGException("Matching algorithm returned an incomplete candidate set.")

        logger.info(
            "Matched job %s against %d eligible profiles; retrieved=%d algorithmically_reranked=%d returned=%d",
            request.job.job_id,
            len(candidates_by_id),
            len(retrieved),
            len(rerank_ids),
            len(matches),
        )
        return self._response(matches)

    async def rerank_jobs_for_freelancer(self, request: JobRerankRequest) -> JobRerankResponse:
        """Reverse of rerank_talent: the freelancer is the query, open job posts are candidates."""
        self._validate_job_request_versions(request)
        candidates_by_id = self._job_candidate_map(request.candidates)
        if not candidates_by_id:
            return self._job_response([])

        documents = {
            job_id: self._job_candidate_document(candidate)
            for job_id, candidate in candidates_by_id.items()
        }
        collection_name = self._job_collection_name()
        await self._upsert_changed_jobs(collection_name, documents)
        retrieved = await self._retrieve_jobs(
            collection_name,
            request.freelancer,
            list(candidates_by_id),
        )

        rerank_limit = min(settings.MATCHING_RERANK_LIMIT, len(retrieved))
        rerank_ids = [job_id for job_id, _ in retrieved[:rerank_limit]]
        algorithm_scores = self._evaluate_job_algorithm(
            request.freelancer,
            rerank_ids,
            candidates_by_id,
        )

        embedding_scores = dict(retrieved)
        matches = [
            JobRerankMatch(
                job_id=job_id,
                embedding_score=embedding_scores[job_id],
                algorithm_score=evaluation[0],
                semantic_strengths=evaluation[1],
                match_reasons=evaluation[2],
            )
            for job_id, evaluation in algorithm_scores.items()
        ]
        matches.sort(
            key=lambda match: (
                -(0.5625 * match.embedding_score + 0.4375 * match.algorithm_score),
                match.job_id,
            )
        )
        expected = min(request.top_k, len(candidates_by_id), rerank_limit)
        matches = matches[:expected]
        if len(matches) != expected:
            raise RAGException("Matching algorithm returned an incomplete candidate set.")

        logger.info(
            "Matched freelancer %s against %d eligible jobs; retrieved=%d algorithmically_reranked=%d returned=%d",
            request.freelancer.freelancer_id,
            len(candidates_by_id),
            len(retrieved),
            len(rerank_ids),
            len(matches),
        )
        return self._job_response(matches)

    def _validate_job_request_versions(self, request: JobRerankRequest) -> None:
        if request.algorithm_version != settings.MATCHING_ALGORITHM_VERSION:
            raise RAGException("Unsupported talent matching algorithm version.")
        if request.scoring_version != settings.MATCHING_SCORING_VERSION:
            raise RAGException("Unsupported talent matching scoring version.")

    @staticmethod
    def _job_candidate_map(
        candidates: List[JobRerankCandidate],
    ) -> Dict[str, JobRerankCandidate]:
        result: Dict[str, JobRerankCandidate] = {}
        for candidate in candidates:
            if candidate.job_id in result:
                raise RAGException("Duplicate job IDs are not allowed.")
            result[candidate.job_id] = candidate
        return result

    async def _upsert_changed_jobs(
        self,
        collection_name: str,
        documents: Dict[str, str],
    ) -> None:
        stable_ids = [self._job_stable_id(job_id) for job_id in documents]
        existing = await asyncio.to_thread(
            self.chroma.get_documents,
            collection_name,
            stable_ids,
        )
        existing_hashes = {
            item_id: (metadata or {}).get("content_hash")
            for item_id, metadata in zip(
                existing.get("ids") or [],
                existing.get("metadatas") or [],
            )
        }
        changed = [
            job_id
            for job_id, document in documents.items()
            if existing_hashes.get(self._job_stable_id(job_id)) != self._hash(document)
        ]

        for start in range(0, len(changed), 100):
            batch_ids = changed[start : start + 100]
            batch_documents = [documents[job_id] for job_id in batch_ids]
            embeddings = await self.rag.get_embeddings(
                batch_documents,
                provider=settings.MATCHING_EMBEDDING_PROVIDER,
                model=settings.MATCHING_EMBEDDING_MODEL,
                allow_fallback=False,
            )
            if len(embeddings) != len(batch_ids):
                raise RAGException("Embedding provider returned an incomplete job batch.")
            await asyncio.to_thread(
                self.chroma.upsert_documents,
                collection_name,
                [self._job_stable_id(job_id) for job_id in batch_ids],
                embeddings,
                batch_documents,
                [
                    {
                        "job_id": job_id,
                        "content_hash": self._hash(documents[job_id]),
                        "embedding_provider": settings.MATCHING_EMBEDDING_PROVIDER,
                        "embedding_model": settings.MATCHING_EMBEDDING_MODEL,
                    }
                    for job_id in batch_ids
                ],
            )

    async def _retrieve_jobs(
        self,
        collection_name: str,
        freelancer: JobRerankFreelancer,
        eligible_ids: List[str],
    ) -> List[tuple[str, float]]:
        query_embeddings = await self.rag.get_embeddings(
            [self._freelancer_document(freelancer)],
            provider=settings.MATCHING_EMBEDDING_PROVIDER,
            model=settings.MATCHING_EMBEDDING_MODEL,
            allow_fallback=False,
        )
        if len(query_embeddings) != 1:
            raise RAGException("Embedding provider returned an invalid freelancer embedding.")
        freelancer_vector = query_embeddings[0]

        stable_ids = [self._job_stable_id(jid) for jid in eligible_ids]
        existing = await asyncio.to_thread(
            self.chroma.get_documents,
            collection_name,
            stable_ids,
        )

        retrieved_ids = existing.get("ids") if existing.get("ids") is not None else []
        retrieved_embeddings = existing.get("embeddings") if existing.get("embeddings") is not None else []
        retrieved_metadatas = existing.get("metadatas") if existing.get("metadatas") is not None else []

        retrieved_map = {}
        for stable_id, emb, meta in zip(retrieved_ids, retrieved_embeddings, retrieved_metadatas):
            job_id = (meta or {}).get("job_id")
            if (
                not job_id
                or job_id not in eligible_ids
                or stable_id != self._job_stable_id(job_id)
                or job_id in retrieved_map
            ):
                raise RAGException("Chroma returned an unknown or duplicate job ID.")
            retrieved_map[job_id] = (stable_id, emb)

        missing = [jid for jid in eligible_ids if jid not in retrieved_map]
        if missing:
            raise RAGException(
                f"Chroma returned an incomplete retrieval result. Missing job profiles: {', '.join(missing)}"
            )

        retrieved: List[tuple[str, float]] = []
        for job_id in eligible_ids:
            _, emb = retrieved_map[job_id]
            dot_product = sum(a * b for a, b in zip(freelancer_vector, emb))
            norm_a = math.sqrt(sum(a * a for a in freelancer_vector))
            norm_b = math.sqrt(sum(b * b for b in emb))
            similarity = dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0
            similarity_score = max(0.0, min(100.0, similarity * 100.0))
            retrieved.append((job_id, round(similarity_score, 2)))

        retrieved.sort(key=lambda item: (-item[1], item[0]))
        retrieval_count = min(settings.MATCHING_RETRIEVAL_LIMIT, len(eligible_ids))
        return retrieved[:retrieval_count]

    def _evaluate_job_algorithm(
        self,
        freelancer: JobRerankFreelancer,
        job_ids: List[str],
        candidates: Dict[str, JobRerankCandidate],
    ) -> Dict[str, tuple[float, List[str], List[str]]]:
        job_documents = {
            job_id: self._job_candidate_tokens(candidates[job_id])
            for job_id in job_ids
        }
        idf = self._inverse_document_frequency(job_documents.values())
        freelancer_role_tokens = self._tokens(
            freelancer.title,
            freelancer.major_name,
            *freelancer.categories,
            *(work.title for work in freelancer.verified_work),
            *(work.major_name for work in freelancer.verified_work),
            *(work.category_name for work in freelancer.verified_work),
        )
        freelancer_task_tokens = self._tokens(
            freelancer.title,
            freelancer.bio,
            *(work.title for work in freelancer.verified_work),
            *(work.description for work in freelancer.verified_work),
        )
        freelancer_skill_phrases = self._phrases(
            [
                *freelancer.skills,
                *(skill for work in freelancer.verified_work for skill in work.skills),
            ]
        )

        evaluations: Dict[str, tuple[float, List[str], List[str]]] = {}
        for job_id in job_ids:
            job = candidates[job_id]
            role_tokens = self._tokens(
                job.title,
                job.industry,
                job.major_name,
                job.category_name,
            )
            task_tokens = self._tokens(job.title, job.description)
            job_skill_phrases = self._phrases([*job.skills, *job.custom_skills])

            role_score = self._token_relevance(freelancer_role_tokens, role_tokens, idf)
            task_score = self._token_relevance(freelancer_task_tokens, task_tokens, idf)
            skill_score = self._job_skill_relevance(freelancer_skill_phrases, job_skill_phrases)

            components: List[tuple[float, float]] = [
                (35.0, role_score),
                (35.0, task_score),
            ]
            if job_skill_phrases:
                components.append((30.0, skill_score))
            total_weight = sum(weight for weight, _ in components)
            algorithm_score = sum(weight * score for weight, score in components) / total_weight

            strengths: List[str] = []
            if role_score >= 55:
                strengths.append("Major and category alignment")
            if task_score >= 45:
                strengths.append("Profile language overlaps the job description")
            if job_skill_phrases and skill_score >= 60:
                strengths.append("Strong skill coverage")
            if not strengths:
                strengths.append("Embedding similarity is the primary relevance signal")

            reasons = [
                f"Algorithmic role/domain alignment: {role_score:.0f}/100",
                f"Algorithmic task alignment: {task_score:.0f}/100",
            ]
            if job_skill_phrases:
                reasons.append(f"Algorithmic skill relevance: {skill_score:.0f}/100")

            evaluations[job_id] = (
                round(max(0.0, min(100.0, algorithm_score)), 2),
                strengths[:5],
                reasons[:3],
            )
        return evaluations

    def _job_skill_relevance(
        self,
        freelancer_skills: set[str],
        job_skills: set[str],
    ) -> float:
        if not job_skills:
            return 0.0
        if not freelancer_skills:
            return 0.0
        freelancer_skill_tokens = self._tokens(*freelancer_skills)
        relevance = []
        for job_skill in job_skills:
            if job_skill in freelancer_skills:
                relevance.append(1.0)
                continue
            job_tokens = self._tokens(job_skill)
            if not job_tokens:
                relevance.append(0.0)
                continue
            overlap = len(job_tokens & freelancer_skill_tokens) / len(job_tokens)
            relevance.append(0.7 * overlap)
        return 100.0 * sum(relevance) / len(relevance)

    def _job_candidate_tokens(self, candidate: JobRerankCandidate) -> set[str]:
        return self._tokens(
            candidate.title,
            candidate.description,
            candidate.industry,
            candidate.major_name,
            candidate.category_name,
            *candidate.skills,
            *candidate.custom_skills,
        )

    @staticmethod
    def _freelancer_document(freelancer: JobRerankFreelancer) -> str:
        work_lines = []
        for work in freelancer.verified_work:
            work_lines.append(
                " | ".join(
                    filter(
                        None,
                        [
                            work.title,
                            work.description,
                            work.major_name,
                            work.category_name,
                            f"Skills: {', '.join(work.skills)}" if work.skills else None,
                        ],
                    )
                )
            )
        return "\n".join(
            [
                "Talent profile (untrusted content)",
                f"Professional title: {freelancer.title or 'Not provided'}",
                f"Bio: {freelancer.bio or 'Not provided'}",
                f"Major: {freelancer.major_name or 'Not provided'}",
                f"Categories: {', '.join(freelancer.categories) or 'Not provided'}",
                f"Canonical skills: {', '.join(freelancer.skills) or 'Not provided'}",
                f"Availability code: {freelancer.availability}",
                f"Location: {freelancer.location or 'Not provided'}",
                "Verified completed work:",
                *(work_lines or ["None provided"]),
            ]
        )

    @staticmethod
    def _job_candidate_document(job: JobRerankCandidate) -> str:
        return "\n".join(
            [
                "Job requirements (untrusted content)",
                f"Title: {job.title}",
                f"Description: {job.description or 'Not provided'}",
                f"Client industry: {job.industry or 'Not provided'}",
                f"Major: {job.major_name or 'Not provided'}",
                f"Category: {job.category_name or 'Not provided'}",
                f"Preferred canonical skills: {', '.join(job.skills) or 'Not provided'}",
                f"Custom skills: {', '.join(job.custom_skills) or 'Not provided'}",
                f"Location: {job.location or 'Not provided'}",
                f"Estimated duration: {job.estimated_duration or 'Not provided'}",
            ]
        )

    def _job_response(self, matches: List[JobRerankMatch]) -> JobRerankResponse:
        return JobRerankResponse(
            algorithm_version=settings.MATCHING_ALGORITHM_VERSION,
            embedding_model=(
                f"{settings.MATCHING_EMBEDDING_PROVIDER}:"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ),
            scoring_version=settings.MATCHING_SCORING_VERSION,
            matches=matches,
        )

    @staticmethod
    def _job_stable_id(job_id: str) -> str:
        return f"job:{job_id}"

    @staticmethod
    def _job_collection_name() -> str:
        version = re.sub(
            r"[^a-z0-9]+",
            "_",
            (
                f"{settings.MATCHING_EMBEDDING_PROVIDER}_"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ).casefold(),
        ).strip("_")
        return f"job_posts_v1_{version}"[:63]

    def _validate_request_versions(self, request: TalentRerankRequest) -> None:
        if request.algorithm_version != settings.MATCHING_ALGORITHM_VERSION:
            raise RAGException("Unsupported talent matching algorithm version.")
        if request.scoring_version != settings.MATCHING_SCORING_VERSION:
            raise RAGException("Unsupported talent matching scoring version.")

    @staticmethod
    def _candidate_map(
        candidates: List[TalentRerankCandidate],
    ) -> Dict[str, TalentRerankCandidate]:
        result: Dict[str, TalentRerankCandidate] = {}
        for candidate in candidates:
            if candidate.freelancer_id in result:
                raise RAGException("Duplicate freelancer IDs are not allowed.")
            result[candidate.freelancer_id] = candidate
        return result

    async def _upsert_changed_profiles(
        self,
        collection_name: str,
        documents: Dict[str, str],
    ) -> None:
        stable_ids = [self._stable_id(candidate_id) for candidate_id in documents]
        existing = await asyncio.to_thread(
            self.chroma.get_documents,
            collection_name,
            stable_ids,
        )
        existing_hashes = {
            item_id: (metadata or {}).get("content_hash")
            for item_id, metadata in zip(
                existing.get("ids") or [],
                existing.get("metadatas") or [],
            )
        }
        changed = [
            candidate_id
            for candidate_id, document in documents.items()
            if existing_hashes.get(self._stable_id(candidate_id)) != self._hash(document)
        ]

        for start in range(0, len(changed), 100):
            batch_ids = changed[start : start + 100]
            batch_documents = [documents[candidate_id] for candidate_id in batch_ids]
            embeddings = await self.rag.get_embeddings(
                batch_documents,
                provider=settings.MATCHING_EMBEDDING_PROVIDER,
                model=settings.MATCHING_EMBEDDING_MODEL,
                allow_fallback=False,
            )
            if len(embeddings) != len(batch_ids):
                raise RAGException("Embedding provider returned an incomplete profile batch.")
            await asyncio.to_thread(
                self.chroma.upsert_documents,
                collection_name,
                [self._stable_id(candidate_id) for candidate_id in batch_ids],
                embeddings,
                batch_documents,
                [
                    {
                        "freelancer_id": candidate_id,
                        "content_hash": self._hash(documents[candidate_id]),
                        "embedding_provider": settings.MATCHING_EMBEDDING_PROVIDER,
                        "embedding_model": settings.MATCHING_EMBEDDING_MODEL,
                    }
                    for candidate_id in batch_ids
                ],
            )

    async def _retrieve(
        self,
        collection_name: str,
        job: TalentRerankJob,
        eligible_ids: List[str],
    ) -> List[tuple[str, float]]:
        query_embeddings = await self.rag.get_embeddings(
            [self._job_document(job)],
            provider=settings.MATCHING_EMBEDDING_PROVIDER,
            model=settings.MATCHING_EMBEDDING_MODEL,
            allow_fallback=False,
        )
        if len(query_embeddings) != 1:
            raise RAGException("Embedding provider returned an invalid job embedding.")
        job_vector = query_embeddings[0]

        stable_ids = [self._stable_id(cid) for cid in eligible_ids]
        existing = await asyncio.to_thread(
            self.chroma.get_documents,
            collection_name,
            stable_ids,
        )

        retrieved_ids = existing.get("ids") if existing.get("ids") is not None else []
        retrieved_embeddings = existing.get("embeddings") if existing.get("embeddings") is not None else []
        retrieved_metadatas = existing.get("metadatas") if existing.get("metadatas") is not None else []

        retrieved_map = {}
        for stable_id, emb, meta in zip(retrieved_ids, retrieved_embeddings, retrieved_metadatas):
            candidate_id = (meta or {}).get("freelancer_id")
            if (
                not candidate_id
                or candidate_id not in eligible_ids
                or stable_id != self._stable_id(candidate_id)
                or candidate_id in retrieved_map
            ):
                raise RAGException("Chroma returned an unknown or duplicate freelancer ID.")
            retrieved_map[candidate_id] = (stable_id, emb)

        missing = [cid for cid in eligible_ids if cid not in retrieved_map]
        if missing:
            raise RAGException(
                f"Chroma returned an incomplete retrieval result. Missing freelancer profiles: {', '.join(missing)}"
            )

        retrieved: List[tuple[str, float]] = []
        for candidate_id in eligible_ids:
            _, emb = retrieved_map[candidate_id]
            dot_product = sum(a * b for a, b in zip(job_vector, emb))
            norm_a = math.sqrt(sum(a * a for a in job_vector))
            norm_b = math.sqrt(sum(b * b for b in emb))
            similarity = dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0
            similarity_score = max(0.0, min(100.0, similarity * 100.0))
            retrieved.append((candidate_id, round(similarity_score, 2)))

        retrieved.sort(key=lambda item: (-item[1], item[0]))
        retrieval_count = min(settings.MATCHING_RETRIEVAL_LIMIT, len(eligible_ids))
        return retrieved[:retrieval_count]

    def _evaluate_algorithm(
        self,
        job: TalentRerankJob,
        candidate_ids: List[str],
        candidates: Dict[str, TalentRerankCandidate],
    ) -> Dict[str, tuple[float, List[str], List[str]]]:
        candidate_documents = {
            candidate_id: self._candidate_tokens(candidates[candidate_id])
            for candidate_id in candidate_ids
        }
        idf = self._inverse_document_frequency(candidate_documents.values())
        job_role_tokens = self._tokens(
            job.title,
            job.industry,
            job.major_name,
            job.category_name,
        )
        job_task_tokens = self._tokens(job.title, job.description)
        job_skill_phrases = self._phrases([*job.skills, *job.custom_skills])

        evaluations: Dict[str, tuple[float, List[str], List[str]]] = {}
        for candidate_id in candidate_ids:
            candidate = candidates[candidate_id]
            role_tokens = self._tokens(
                candidate.title,
                candidate.major_name,
                *candidate.categories,
                *(work.title for work in candidate.verified_work),
                *(work.major_name for work in candidate.verified_work),
                *(work.category_name for work in candidate.verified_work),
            )
            task_tokens = self._tokens(
                candidate.title,
                candidate.bio,
                *(work.title for work in candidate.verified_work),
                *(work.description for work in candidate.verified_work),
            )
            role_score = self._token_relevance(job_role_tokens, role_tokens, idf)
            task_score = self._token_relevance(job_task_tokens, task_tokens, idf)
            skill_score = self._skill_relevance(job_skill_phrases, candidate)
            verified_work_score = self._verified_work_relevance(job, candidate, idf)

            components: List[tuple[float, float]] = [
                (30.0, role_score),
                (30.0, task_score),
                (15.0, verified_work_score),
            ]
            if job_skill_phrases:
                components.append((25.0, skill_score))
            total_weight = sum(weight for weight, _ in components)
            algorithm_score = sum(weight * score for weight, score in components) / total_weight

            strengths: List[str] = []
            if role_score >= 55:
                strengths.append("Professional role and domain alignment")
            if task_score >= 45:
                strengths.append("Profile language overlaps the requested work")
            if job_skill_phrases and skill_score >= 60:
                strengths.append("Strong preferred-skill coverage")
            if verified_work_score >= 45:
                strengths.append("Relevant verified completed work")
            if not strengths:
                strengths.append("Embedding similarity is the primary relevance signal")

            reasons = [
                f"Algorithmic role/domain alignment: {role_score:.0f}/100",
                f"Algorithmic task alignment: {task_score:.0f}/100",
            ]
            if job_skill_phrases:
                reasons.append(f"Algorithmic preferred-skill relevance: {skill_score:.0f}/100")
            else:
                reasons.append(f"Algorithmic verified-work relevance: {verified_work_score:.0f}/100")

            evaluations[candidate_id] = (
                round(max(0.0, min(100.0, algorithm_score)), 2),
                strengths[:5],
                reasons[:3],
            )
        return evaluations

    def _verified_work_relevance(
        self,
        job: TalentRerankJob,
        candidate: TalentRerankCandidate,
        idf: Dict[str, float],
    ) -> float:
        if not candidate.verified_work:
            return 0.0
        job_tokens = self._tokens(
            job.title,
            job.description,
            job.major_name,
            job.category_name,
            *job.skills,
            *job.custom_skills,
        )
        work_scores = [
            self._token_relevance(
                job_tokens,
                self._tokens(
                    work.title,
                    work.description,
                    work.major_name,
                    work.category_name,
                    *work.skills,
                ),
                idf,
            )
            for work in candidate.verified_work
        ]
        return max(work_scores, default=0.0)

    def _skill_relevance(
        self,
        job_skills: set[str],
        candidate: TalentRerankCandidate,
    ) -> float:
        if not job_skills:
            return 0.0
        candidate_skills = self._phrases(
            [
                *candidate.skills,
                *(skill for work in candidate.verified_work for skill in work.skills),
            ]
        )
        candidate_skill_tokens = self._tokens(*candidate_skills)
        relevance = []
        for job_skill in job_skills:
            if job_skill in candidate_skills:
                relevance.append(1.0)
                continue
            job_tokens = self._tokens(job_skill)
            if not job_tokens:
                relevance.append(0.0)
                continue
            overlap = len(job_tokens & candidate_skill_tokens) / len(job_tokens)
            relevance.append(0.7 * overlap)
        return 100.0 * sum(relevance) / len(relevance)

    @staticmethod
    def _token_relevance(
        query_tokens: set[str],
        document_tokens: set[str],
        idf: Dict[str, float],
    ) -> float:
        if not query_tokens or not document_tokens:
            return 0.0
        intersection = query_tokens & document_tokens
        query_weight = sum(idf.get(token, 1.0) for token in query_tokens)
        matched_weight = sum(idf.get(token, 1.0) for token in intersection)
        coverage = matched_weight / query_weight if query_weight else 0.0
        dice = 2.0 * len(intersection) / (len(query_tokens) + len(document_tokens))
        return round(100.0 * (0.8 * coverage + 0.2 * dice), 2)

    @staticmethod
    def _inverse_document_frequency(
        documents: Iterable[set[str]],
    ) -> Dict[str, float]:
        document_list = list(documents)
        count = len(document_list)
        frequencies: Counter[str] = Counter(
            token for document in document_list for token in document
        )
        return {
            token: math.log((count + 1) / (frequency + 1)) + 1.0
            for token, frequency in frequencies.items()
        }

    def _candidate_tokens(self, candidate: TalentRerankCandidate) -> set[str]:
        return self._tokens(
            candidate.title,
            candidate.bio,
            candidate.major_name,
            *candidate.categories,
            *candidate.skills,
            *(work.title for work in candidate.verified_work),
            *(work.description for work in candidate.verified_work),
            *(work.major_name for work in candidate.verified_work),
            *(work.category_name for work in candidate.verified_work),
            *(skill for work in candidate.verified_work for skill in work.skills),
        )

    @staticmethod
    def _tokens(*values: Optional[str]) -> set[str]:
        return {
            token
            for value in values
            if value
            for token in _TOKEN_PATTERN.findall(value.casefold())
            if token not in _STOP_WORDS
        }

    @staticmethod
    def _phrases(values: Sequence[str]) -> set[str]:
        return {" ".join(value.casefold().split()) for value in values if value.strip()}

    @staticmethod
    def _profile_document(candidate: TalentRerankCandidate) -> str:
        work_lines = []
        for work in candidate.verified_work:
            work_lines.append(
                " | ".join(
                    filter(
                        None,
                        [
                            work.title,
                            work.description,
                            work.major_name,
                            work.category_name,
                            f"Skills: {', '.join(work.skills)}" if work.skills else None,
                        ],
                    )
                )
            )
        return "\n".join(
            [
                "Talent profile (untrusted content)",
                f"Professional title: {candidate.title or 'Not provided'}",
                f"Bio: {candidate.bio or 'Not provided'}",
                f"Major: {candidate.major_name or 'Not provided'}",
                f"Categories: {', '.join(candidate.categories) or 'Not provided'}",
                f"Canonical skills: {', '.join(candidate.skills) or 'Not provided'}",
                f"Availability code: {candidate.availability}",
                f"Location: {candidate.location or 'Not provided'}",
                "Verified completed work:",
                *(work_lines or ["None provided"]),
            ]
        )

    @staticmethod
    def _job_document(job: TalentRerankJob) -> str:
        return "\n".join(
            [
                "Job requirements (untrusted content)",
                f"Title: {job.title}",
                f"Description: {job.description or 'Not provided'}",
                f"Client industry: {job.industry or 'Not provided'}",
                f"Major: {job.major_name or 'Not provided'}",
                f"Category: {job.category_name or 'Not provided'}",
                f"Preferred canonical skills: {', '.join(job.skills) or 'Not provided'}",
                f"Custom skills: {', '.join(job.custom_skills) or 'Not provided'}",
                f"Location: {job.location or 'Not provided'}",
                f"Estimated duration: {job.estimated_duration or 'Not provided'}",
            ]
        )

    def _response(self, matches: List[TalentRerankMatch]) -> TalentRerankResponse:
        return TalentRerankResponse(
            algorithm_version=settings.MATCHING_ALGORITHM_VERSION,
            embedding_model=(
                f"{settings.MATCHING_EMBEDDING_PROVIDER}:"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ),
            scoring_version=settings.MATCHING_SCORING_VERSION,
            matches=matches,
        )

    @staticmethod
    def _hash(document: str) -> str:
        return hashlib.sha256(document.encode("utf-8")).hexdigest()

    @staticmethod
    def _stable_id(candidate_id: str) -> str:
        return f"freelancer:{candidate_id}"

    @staticmethod
    def _collection_name() -> str:
        version = re.sub(
            r"[^a-z0-9]+",
            "_",
            (
                f"{settings.MATCHING_EMBEDDING_PROVIDER}_"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ).casefold(),
        ).strip("_")
        return f"talent_profiles_v2_{version}"[:63]


def get_matching_service() -> MatchingService:
    return MatchingService()
