from __future__ import annotations

import os
from collections import defaultdict
import psutil
from fastapi import APIRouter, HTTPException

from app.schemas.eval_schemas import (
    RetrievalEvalResponse,
    AnswerEvalResponse,
    EvidenceEvalRequest,
    EvidenceEvalResponse,
    SystemStatsResponse,
)
from app.services.evaluator import EvidenceEvaluatorService
from evaluation.eval import evaluate_all_retrieval, evaluate_all_answers

router = APIRouter()
_evaluator_service = EvidenceEvaluatorService()


@router.post("/eval/retrieval", response_model=RetrievalEvalResponse, tags=["RAG Evaluation"])
async def run_retrieval_eval():
    """Run full retrieval benchmark evaluation and compute aggregate metrics."""
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    category_mrr_map = defaultdict(list)
    count = 0

    for test, result, _ in evaluate_all_retrieval():
        count += 1
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_coverage += result.keyword_coverage
        category_mrr_map[test.category].append(result.mrr)

    if count == 0:
        raise HTTPException(status_code=500, detail="No retrieval test items found.")

    avg_mrr = round(total_mrr / count, 4)
    avg_ndcg = round(total_ndcg / count, 4)
    avg_coverage = round(total_coverage / count, 2)

    cat_mrr_summary = {
        cat: round(sum(scores) / len(scores), 4) for cat, scores in category_mrr_map.items()
    }

    return RetrievalEvalResponse(
        avg_mrr=avg_mrr,
        avg_ndcg=avg_ndcg,
        avg_coverage=avg_coverage,
        test_count=count,
        category_mrr=cat_mrr_summary,
    )


@router.post("/eval/answer", response_model=AnswerEvalResponse, tags=["RAG Evaluation"])
async def run_answer_eval():
    """Run full answer quality benchmark evaluation and compute aggregate metrics."""
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0
    category_acc_map = defaultdict(list)
    count = 0

    for test, result, _ in evaluate_all_answers():
        count += 1
        total_accuracy += result.accuracy
        total_completeness += result.completeness
        total_relevance += result.relevance
        category_acc_map[test.category].append(result.accuracy)

    if count == 0:
        raise HTTPException(status_code=500, detail="No answer test items found.")

    avg_acc = round(total_accuracy / count, 2)
    avg_comp = round(total_completeness / count, 2)
    avg_rel = round(total_relevance / count, 2)

    cat_acc_summary = {
        cat: round(sum(scores) / len(scores), 2) for cat, scores in category_acc_map.items()
    }

    return AnswerEvalResponse(
        avg_accuracy=avg_acc,
        avg_completeness=avg_comp,
        avg_relevance=avg_rel,
        test_count=count,
        category_accuracy=cat_acc_summary,
    )


@router.post("/evaluate-evidence", response_model=EvidenceEvalResponse, tags=["RAG Evaluation"])
async def evaluate_evidence(payload: EvidenceEvalRequest):
    """Evaluate candidate evidence text for factual truthfulness against source context."""
    try:
        return _evaluator_service.evaluate(payload.source_context, payload.candidate_evidence)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evidence evaluation failed: {exc}")


@router.get("/system-stats", response_model=SystemStatsResponse, tags=["System Health"])
async def get_system_stats():
    """Get live EC2 system RAM and process RAM stats."""
    mem = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    proc_ram_mb = proc.memory_info().rss / (1024 * 1024)

    return SystemStatsResponse(
        system_ram_used_gb=round(mem.used / (1024**3), 2),
        system_ram_total_gb=round(mem.total / (1024**3), 2),
        system_ram_percent=round(mem.percent, 1),
        ai_process_ram_mb=round(proc_ram_mb, 1),
        status="healthy",
    )
