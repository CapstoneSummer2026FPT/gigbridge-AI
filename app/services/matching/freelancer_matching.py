"""
PURPOSE: Freelancer job matching service for recommending and reranking open job posts for a candidate.
IMPORTANCE: Critical — Primary AI matching engine for freelancer job discovery ("browse jobs").
READING FLOW: app/schemas/matching.py -> app/services/matching/matching_base.py -> app/services/matching/freelancer_matching.py -> app/api/routes/matching.py
"""

import asyncio
import math
import logging
from typing import Dict, List, Optional, Tuple

from app.schemas.matching import (
    JobRerankCandidate,
    JobRerankFreelancer,
    JobRerankMatch,
    JobRerankRequest,
    JobRerankResponse,
)
from app.core.config import settings
from app.core.exceptions import RAGException
from app.services.matching.matching_base import MatchingBaseService

logger = logging.getLogger("ai_server.freelancer_matching_service")


class FreelancerMatchingService(MatchingBaseService):
    """Reranks open job post candidates for a target freelancer query profile."""

    async def rerank_jobs_for_freelancer(self, request: JobRerankRequest) -> JobRerankResponse:
        """Rerank open job post candidates for a target freelancer.
        
        Reverse of candidate matching: the freelancer is the query, and job posts are candidates.
        Flow:
        1. Validate request algorithm and scoring versions.
        2. Map job candidates into lookup dictionary.
        3. Upsert changed job requirement documents into Chroma DB vector store.
        4. Perform vector similarity retrieval against freelancer query embedding.
        5. Evaluate deterministic algorithmic scoring (role alignment, task overlap, skills).
        6. Combine vector similarity and algorithm score into final weighted ranking.
        7. Sort, truncate to top_k, and return structured JobRerankResponse.
        """
        self._validate_job_request_versions(request)
        candidates_by_id = self._job_candidate_map(request.candidates)
        if not candidates_by_id:
            return self._job_response([])

        documents = {
            job_id: self._job_candidate_document(candidate)
            for job_id, candidate in candidates_by_id.items()
        }
        collection_name = self.collection_name_jobs()
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
        """Validate algorithm and scoring version fields in job rerank request."""
        if request.algorithm_version != settings.MATCHING_ALGORITHM_VERSION:
            raise RAGException("Unsupported talent matching algorithm version.")
        if request.scoring_version != settings.MATCHING_SCORING_VERSION:
            raise RAGException("Unsupported talent matching scoring version.")

    @staticmethod
    def _job_candidate_map(
        candidates: List[JobRerankCandidate],
    ) -> Dict[str, JobRerankCandidate]:
        """Convert list of job candidates into a unique job_id lookup map."""
        result: Dict[str, JobRerankCandidate] = {}
        for candidate in candidates:
            if candidate.job_id in result:
                raise RAGException("Duplicate job IDs are not allowed.")
            result[candidate.job_id] = candidate
        return result

    @staticmethod
    def _job_candidate_document(job: JobRerankCandidate) -> str:
        """Format job post requirement attributes into plain text for vector embedding."""
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

    @staticmethod
    def _freelancer_document(freelancer: JobRerankFreelancer) -> str:
        """Format freelancer profile attributes into plain text for query vector embedding."""
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

    async def _upsert_changed_jobs(
        self,
        collection_name: str,
        documents: Dict[str, str],
    ) -> None:
        """Batch upsert job requirement embeddings into Chroma DB if content hash has changed."""
        stable_ids = [self.stable_job_id(job_id) for job_id in documents]
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
            if existing_hashes.get(self.stable_job_id(job_id)) != self.hash_text(document)
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
                [self.stable_job_id(job_id) for job_id in batch_ids],
                embeddings,
                batch_documents,
                [
                    {
                        "job_id": job_id,
                        "content_hash": self.hash_text(documents[job_id]),
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
    ) -> List[Tuple[str, float]]:
        """Retrieve job requirement vectors from Chroma DB and compute cosine similarity against freelancer vector."""
        query_embeddings = await self.rag.get_embeddings(
            [self._freelancer_document(freelancer)],
            provider=settings.MATCHING_EMBEDDING_PROVIDER,
            model=settings.MATCHING_EMBEDDING_MODEL,
            allow_fallback=False,
        )
        if len(query_embeddings) != 1:
            raise RAGException("Embedding provider returned an invalid freelancer embedding.")
        freelancer_vector = query_embeddings[0]

        stable_ids = [self.stable_job_id(jid) for jid in eligible_ids]
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
                or stable_id != self.stable_job_id(job_id)
                or job_id in retrieved_map
            ):
                raise RAGException("Chroma returned an unknown or duplicate job ID.")
            retrieved_map[job_id] = (stable_id, emb)

        missing = [jid for jid in eligible_ids if jid not in retrieved_map]
        if missing:
            raise RAGException(
                f"Chroma returned an incomplete retrieval result. Missing job profiles: {', '.join(missing)}"
            )

        retrieved: List[Tuple[str, float]] = []
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
    ) -> Dict[str, Tuple[float, List[str], List[str]]]:
        """Compute weighted feature algorithm scores for job candidates against freelancer profile."""
        job_documents = {
            job_id: self._job_candidate_tokens(candidates[job_id])
            for job_id in job_ids
        }
        idf = self.compute_idf(job_documents.values())
        freelancer_role_tokens = self.extract_tokens(
            freelancer.title,
            freelancer.major_name,
            *freelancer.categories,
            *(work.title for work in freelancer.verified_work),
            *(work.major_name for work in freelancer.verified_work),
            *(work.category_name for work in freelancer.verified_work),
        )
        freelancer_task_tokens = self.extract_tokens(
            freelancer.title,
            freelancer.bio,
            *(work.title for work in freelancer.verified_work),
            *(work.description for work in freelancer.verified_work),
        )
        freelancer_skill_phrases = self.extract_phrases(
            [
                *freelancer.skills,
                *(skill for work in freelancer.verified_work for skill in work.skills),
            ]
        )

        evaluations: Dict[str, Tuple[float, List[str], List[str]]] = {}
        for job_id in job_ids:
            job = candidates[job_id]
            role_tokens = self.extract_tokens(
                job.title,
                job.industry,
                job.major_name,
                job.category_name,
            )
            task_tokens = self.extract_tokens(job.title, job.description)
            job_skill_phrases = self.extract_phrases([*job.skills, *job.custom_skills])

            role_score = self.compute_token_relevance(freelancer_role_tokens, role_tokens, idf)
            task_score = self.compute_token_relevance(freelancer_task_tokens, task_tokens, idf)
            skill_score = self._job_skill_relevance(freelancer_skill_phrases, job_skill_phrases)

            components: List[Tuple[float, float]] = [
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
        """Calculate skill phrase overlap score between freelancer skills and job skills."""
        if not job_skills or not freelancer_skills:
            return 0.0
        freelancer_skill_tokens = self.extract_tokens(*freelancer_skills)
        relevance = []
        for job_skill in job_skills:
            if job_skill in freelancer_skills:
                relevance.append(1.0)
                continue
            job_tokens = self.extract_tokens(job_skill)
            if not job_tokens:
                relevance.append(0.0)
                continue
            overlap = len(job_tokens & freelancer_skill_tokens) / len(job_tokens)
            relevance.append(0.7 * overlap)
        return 100.0 * sum(relevance) / len(relevance)

    def _job_candidate_tokens(self, candidate: JobRerankCandidate) -> set[str]:
        """Extract all tokens from a job candidate profile."""
        return self.extract_tokens(
            candidate.title,
            candidate.description,
            candidate.industry,
            candidate.major_name,
            candidate.category_name,
            *candidate.skills,
            *candidate.custom_skills,
        )

    def _job_response(self, matches: List[JobRerankMatch]) -> JobRerankResponse:
        """Construct structured JobRerankResponse object."""
        return JobRerankResponse(
            algorithm_version=settings.MATCHING_ALGORITHM_VERSION,
            embedding_model=(
                f"{settings.MATCHING_EMBEDDING_PROVIDER}:"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ),
            scoring_version=settings.MATCHING_SCORING_VERSION,
            matches=matches,
        )
