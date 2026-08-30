"""
PURPOSE: Candidate talent matching service for evaluating and reranking freelancer profiles against job post requirements.
IMPORTANCE: Critical — Primary AI matching engine for client candidate discovery.
READING FLOW: app/schemas/matching.py -> app/services/matching/matching_base.py -> app/services/matching/job_matching.py -> app/api/routes/matching.py
"""

import asyncio
import logging
import math
import re
from typing import Dict, List, Optional, Tuple

from app.schemas.matching import (
    TalentRerankCandidate,
    TalentRerankJob,
    TalentRerankMatch,
    TalentRerankRequest,
    TalentRerankResponse,
)
from app.core.config import settings
from app.core.exceptions import RAGException
from app.services.matching.matching_base import MatchingBaseService

logger = logging.getLogger("ai_server.job_matching_service")


class JobMatchingService(MatchingBaseService):
    """Reranks candidate freelancer profiles against a target job post requirement."""

    async def rerank_talent(self, request: TalentRerankRequest) -> TalentRerankResponse:
        """Rerank candidate freelancer profiles for a given job requirement post.
        
        Flow:
        1. Validate request versions against supported algorithm and scoring settings.
        2. Map candidate profiles into a candidate lookup map.
        3. Upsert changed candidate profile documents into Chroma DB vector store.
        4. Perform vector similarity retrieval against job requirement embedding.
        5. Evaluate deterministic algorithmic scoring (role alignment, task overlap, skills, verified work).
        6. Combine vector similarity and algorithm score into final weighted ranking.
        7. Sort, truncate to top_k, and return structured TalentRerankResponse.
        """
        self._validate_request_versions(request)
        candidates_by_id = self._candidate_map(request.candidates)
        if not candidates_by_id:
            return self._response([])

        documents = {
            candidate_id: self._profile_document(candidate)
            for candidate_id, candidate in candidates_by_id.items()
        }
        collection_name = self.collection_name_talent()
        await self._upsert_changed_profiles(collection_name, documents)
        retrieved = await self._retrieve_freelancers(
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
                saving_percentage=evaluation[3],
                budget_bonus=evaluation[4],
            )
            for candidate_id, evaluation in algorithm_scores.items()
        ]
        matches.sort(
            key=lambda match: (
                -(0.50 * match.embedding_score + 0.50 * match.algorithm_score),
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

    def _validate_request_versions(self, request: TalentRerankRequest) -> None:
        """Validate algorithm and scoring version fields in request."""
        if request.algorithm_version != settings.MATCHING_ALGORITHM_VERSION:
            raise RAGException("Unsupported talent matching algorithm version.")
        if request.scoring_version != settings.MATCHING_SCORING_VERSION:
            raise RAGException("Unsupported talent matching scoring version.")

    @staticmethod
    def _candidate_map(
        candidates: List[TalentRerankCandidate],
    ) -> Dict[str, TalentRerankCandidate]:
        """Convert list of candidates into a unique freelancer_id lookup map."""
        result: Dict[str, TalentRerankCandidate] = {}
        for candidate in candidates:
            if candidate.freelancer_id in result:
                raise RAGException("Duplicate freelancer IDs are not allowed.")
            result[candidate.freelancer_id] = candidate
        return result

    @staticmethod
    def _profile_document(freelancer: TalentRerankCandidate) -> str:
        """Format candidate freelancer profile attributes into plain text for vector embedding."""
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
    def _job_document(job: TalentRerankJob) -> str:
        """Format job post requirement attributes into plain text for vector embedding query."""
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

    async def _upsert_changed_profiles(
        self,
        collection_name: str,
        documents: Dict[str, str],
    ) -> None:
        """Batch upsert candidate profile embeddings into Chroma DB if content hash has changed."""
        stable_ids = [self.stable_freelancer_id(candidate_id) for candidate_id in documents]
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
            if existing_hashes.get(self.stable_freelancer_id(candidate_id)) != self.hash_text(document)
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
                [self.stable_freelancer_id(candidate_id) for candidate_id in batch_ids],
                embeddings,
                batch_documents,
                [
                    {
                        "freelancer_id": candidate_id,
                        "content_hash": self.hash_text(documents[candidate_id]),
                        "embedding_provider": settings.MATCHING_EMBEDDING_PROVIDER,
                        "embedding_model": settings.MATCHING_EMBEDDING_MODEL,
                    }
                    for candidate_id in batch_ids
                ],
            )

    async def _retrieve_freelancers(
        self,
        collection_name: str,
        job: TalentRerankJob,
        eligible_ids: List[str],
    ) -> List[Tuple[str, float]]:
        """Retrieve candidate freelancer vectors from Chroma DB and compute cosine similarity against job vector."""
        query_embeddings = await self.rag.get_embeddings(
            [self._job_document(job)],
            provider=settings.MATCHING_EMBEDDING_PROVIDER,
            model=settings.MATCHING_EMBEDDING_MODEL,
            allow_fallback=False,
        )
        if len(query_embeddings) != 1:
            raise RAGException("Embedding provider returned an invalid job embedding.")
        job_vector = query_embeddings[0]

        stable_ids = [self.stable_freelancer_id(cid) for cid in eligible_ids]
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
                or stable_id != self.stable_freelancer_id(candidate_id)
                or candidate_id in retrieved_map
            ):
                raise RAGException("Chroma returned an unknown or duplicate freelancer ID.")
            retrieved_map[candidate_id] = (stable_id, emb)

        missing = [cid for cid in eligible_ids if cid not in retrieved_map]
        if missing:
            raise RAGException(
                f"Chroma returned an incomplete retrieval result. Missing freelancer profiles: {', '.join(missing)}"
            )

        retrieved: List[Tuple[str, float]] = []
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

    @staticmethod
    def parse_duration_to_hours(duration_str: Optional[str]) -> Optional[float]:
        """Convert duration string (e.g. '2 weeks', '5 days', '1 month', '40 hours') to standard working hours."""
        if not duration_str:
            return None
        text = duration_str.strip().lower()
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        value = float(match.group(1))

        if any(unit in text for unit in ["month", "mo"]):
            return value * 160.0
        elif any(unit in text for unit in ["week", "wk"]):
            return value * 40.0
        elif any(unit in text for unit in ["day", "d"]):
            return value * 8.0
        elif any(unit in text for unit in ["hour", "hr", "h"]):
            return value * 1.0
        return None

    def _calculate_budget_bonus(
        self,
        job: TalentRerankJob,
        candidate: TalentRerankCandidate,
    ) -> Tuple[float, Optional[float]]:
        """Calculate saving percentage and bonus points (+0.0 to +20.0 pts) for candidate against job budget.
        
        If job budget or candidate expected rate is missing/null, bonus is 0.0 and saving_pct is None.
        """
        job_budget = job.budget_max or job.budget_amount or job.budget_min
        if not job_budget or job_budget <= 0:
            return 0.0, None

        if job.budget_type and job.budget_type.lower() == "hourly":
            target_hourly_budget = job_budget
        else:
            hours = self.parse_duration_to_hours(job.estimated_duration)
            if hours and hours > 0:
                target_hourly_budget = job_budget / hours
            else:
                target_hourly_budget = job_budget

        candidate_rate = candidate.expected_rate or candidate.rate_min or candidate.rate_max
        if not candidate_rate or candidate_rate <= 0:
            return 0.0, None

        if target_hourly_budget <= 0:
            return 0.0, None

        saving_pct = ((target_hourly_budget - candidate_rate) / target_hourly_budget) * 100.0
        saving_pct_rounded = round(saving_pct, 1)

        if saving_pct > 0:
            budget_bonus = round(min(20.0, max(0.0, saving_pct)), 1)
        else:
            budget_bonus = 0.0

        return budget_bonus, saving_pct_rounded

    def _evaluate_algorithm(
        self,
        job: TalentRerankJob,
        candidate_ids: List[str],
        candidates: Dict[str, TalentRerankCandidate],
    ) -> Dict[str, Tuple[float, List[str], List[str], Optional[float], float]]:
        """Compute weighted feature algorithm scores with budget bonus rewards for each candidate."""
        candidate_documents = {
            candidate_id: self._candidate_tokens(candidates[candidate_id])
            for candidate_id in candidate_ids
        }
        idf = self.compute_idf(candidate_documents.values())
        job_role_tokens = self.extract_tokens(
            job.title,
            job.industry,
            job.major_name,
            job.category_name,
        )
        job_task_tokens = self.extract_tokens(job.title, job.description)
        job_skill_phrases = self.extract_phrases([*job.skills, *job.custom_skills])

        evaluations: Dict[str, Tuple[float, List[str], List[str], Optional[float], float]] = {}
        for candidate_id in candidate_ids:
            candidate = candidates[candidate_id]
            role_tokens = self.extract_tokens(
                candidate.title,
                candidate.major_name,
                *candidate.categories,
                *(work.title for work in candidate.verified_work),
                *(work.major_name for work in candidate.verified_work),
                *(work.category_name for work in candidate.verified_work),
            )
            task_tokens = self.extract_tokens(
                candidate.title,
                candidate.bio,
                *(work.title for work in candidate.verified_work),
                *(work.description for work in candidate.verified_work),
            )
            role_score = self.compute_token_relevance(job_role_tokens, role_tokens, idf)
            task_score = self.compute_token_relevance(job_task_tokens, task_tokens, idf)
            skill_score = self._skill_relevance(job_skill_phrases, candidate)
            verified_work_score = self._verified_work_relevance(job, candidate, idf)

            budget_bonus, saving_pct = self._calculate_budget_bonus(job, candidate)
            components: List[Tuple[float, float]] = [
                (35.0, role_score),
                (35.0, task_score),
                (15.0, verified_work_score),
            ]
            if job_skill_phrases:
                components.append((15.0, skill_score))
            total_weight = sum(weight for weight, _ in components)
            base_score = sum(weight * score for weight, score in components) / total_weight
            final_algorithm_score = round(max(0.0, min(100.0, base_score + budget_bonus)), 2)

            strengths: List[str] = []
            if budget_bonus > 0 and saving_pct is not None:
                strengths.append(f"Cost savings of {saving_pct:.1f}% vs job budget (+{budget_bonus:.1f} pts bonus)")
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

            reasons: List[str] = []
            if budget_bonus > 0 and saving_pct is not None:
                reasons.append(f"Rewarded +{budget_bonus:.1f} pts bonus ({saving_pct:.1f}% cost savings)")
            reasons.append(f"Algorithmic role/domain alignment: {role_score:.0f}/100")
            reasons.append(f"Algorithmic task alignment: {task_score:.0f}/100")
            if len(reasons) < 3 and job_skill_phrases:
                reasons.append(f"Algorithmic preferred-skill relevance: {skill_score:.0f}/100")
            elif len(reasons) < 3:
                reasons.append(f"Algorithmic verified-work relevance: {verified_work_score:.0f}/100")

            evaluations[candidate_id] = (
                final_algorithm_score,
                strengths[:5],
                reasons[:3],
                saving_pct,
                budget_bonus,
            )
        return evaluations


    def _verified_work_relevance(
        self,
        job: TalentRerankJob,
        candidate: TalentRerankCandidate,
        idf: Dict[str, float],
    ) -> float:
        """Calculate token relevance score across freelancer's verified completed work contracts."""
        if not candidate.verified_work:
            return 0.0
        job_tokens = self.extract_tokens(
            job.title,
            job.description,
            job.major_name,
            job.category_name,
            *job.skills,
            *job.custom_skills,
        )
        work_scores = [
            self.compute_token_relevance(
                job_tokens,
                self.extract_tokens(
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
        """Calculate skill phrase overlap score between job skills and freelancer skills."""
        if not job_skills:
            return 0.0
        candidate_skills = self.extract_phrases(
            [
                *candidate.skills,
                *(skill for work in candidate.verified_work for skill in work.skills),
            ]
        )
        candidate_skill_tokens = self.extract_tokens(*candidate_skills)
        relevance = []
        for job_skill in job_skills:
            if job_skill in candidate_skills:
                relevance.append(1.0)
                continue
            job_tokens = self.extract_tokens(job_skill)
            if not job_tokens:
                relevance.append(0.0)
                continue
            overlap = len(job_tokens & candidate_skill_tokens) / len(job_tokens)
            relevance.append(0.7 * overlap)
        return 100.0 * sum(relevance) / len(relevance)

    def _candidate_tokens(self, candidate: TalentRerankCandidate) -> set[str]:
        """Extract all tokens across a candidate's profile and verified work experience."""
        return self.extract_tokens(
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

    def _response(self, matches: List[TalentRerankMatch]) -> TalentRerankResponse:
        """Construct structured TalentRerankResponse object."""
        return TalentRerankResponse(
            algorithm_version=settings.MATCHING_ALGORITHM_VERSION,
            embedding_model=(
                f"{settings.MATCHING_EMBEDDING_PROVIDER}:"
                f"{settings.MATCHING_EMBEDDING_MODEL}"
            ),
            scoring_version=settings.MATCHING_SCORING_VERSION,
            matches=matches,
        )
