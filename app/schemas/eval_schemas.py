from __future__ import annotations

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RetrievalTestResult(BaseModel):
    mrr: float = Field(..., description="Mean Reciprocal Rank score (0.0 - 1.0)")
    ndcg: float = Field(..., description="Normalized Discounted Cumulative Gain score (0.0 - 1.0)")
    keyword_coverage: float = Field(..., description="Keyword coverage percentage (0.0 - 100.0)")
    category: str = Field(default="General", description="Test item category")


class AnswerTestResult(BaseModel):
    accuracy: float = Field(..., description="Accuracy score (1.0 - 5.0)")
    completeness: float = Field(..., description="Completeness score (1.0 - 5.0)")
    relevance: float = Field(..., description="Relevance score (1.0 - 5.0)")
    category: str = Field(default="General", description="Test item category")


class RetrievalEvalResponse(BaseModel):
    avg_mrr: float
    avg_ndcg: float
    avg_coverage: float
    test_count: int
    category_mrr: Dict[str, float]


class AnswerEvalResponse(BaseModel):
    avg_accuracy: float
    avg_completeness: float
    avg_relevance: float
    test_count: int
    category_accuracy: Dict[str, float]


class EvidenceEvalRequest(BaseModel):
    source_context: str = Field(..., description="Raw source text / prompt context against which evidence is checked")
    candidate_evidence: str = Field(..., description="LLM-generated answer or retrieved evidence text to verify")


class ClaimDetail(BaseModel):
    claim: str = Field(..., description="Individual factual claim extracted from candidate evidence")
    status: Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"] = Field(..., description="Verification status")
    reasoning: str = Field(..., description="Explanation of verification verdict")
    source_quote: Optional[str] = Field(default="", description="Matching quote from source text if supported")


class EvidenceEvalResponse(BaseModel):
    truth_percentage: float = Field(..., description="Calculated truthfulness ratio (0.0 - 100.0%)")
    total_claims: int
    supported_claims: int
    partial_claims: int
    unsupported_claims: int
    claims: List[ClaimDetail]
    annotated_html: str = Field(..., description="Sentence-level color-coded HTML string")


class SystemStatsResponse(BaseModel):
    system_ram_used_gb: float
    system_ram_total_gb: float
    system_ram_percent: float
    ai_process_ram_mb: float
    status: str = "healthy"


class JobPostEvalRequest(BaseModel):
    client_prompt: str = Field(..., description="User prompt for job creation e.g. 'Need a Senior Python Backend Dev...'")


class JobPostEvalResponse(BaseModel):
    details: Dict[str, Any]
    hiring_plan: Dict[str, Any]
    jd_quality_score: float
    taxonomy_match_ok: bool
    budget_clamped_ok: bool
    duration_clamped_ok: bool
    skill_recall: float = Field(default=0.0, description="Skill recall score (0.0 - 100.0%)")
    skill_precision: float = Field(default=0.0, description="Skill precision score (0.0 - 100.0%)")
    f1_score: float = Field(default=0.0, description="F1-score (0.0 - 100.0%)")
    budget_variance_gc: float = Field(default=0.0, description="Budget clamping variance in GC")
    summary_html: str


class FunctionBenchmarkResult(BaseModel):
    function_name: str
    task_type: str
    collection_used: str
    benchmark_cases_count: int
    primary_metrics: Dict[str, Any]


class MultiFunctionEvalResponse(BaseModel):
    total_test_cases: int
    overall_system_mrr: float
    overall_system_ndcg: float
    overall_system_coverage: float
    functions: List[FunctionBenchmarkResult]


