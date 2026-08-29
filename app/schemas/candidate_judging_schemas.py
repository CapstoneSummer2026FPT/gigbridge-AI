"""
PURPOSE: Pydantic schemas for AI Candidate Evaluation Engine (Proposal & Vetting Screening Q&A Judging).
IMPORTANCE: Critical — Defines input and output data contracts for qualitative LLM evaluation, deterministic calculations, evidence traces, and verdict badges.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ── Evidence Claim Model ─────────────────────────────────────────────

class EvidenceClaim(BaseModel):
    claim: str = Field(..., description="Extract of candidate's technical claim or assertion")
    source: str = Field(..., description="Field path or source location (e.g. 'proposal.solutionApproach', 'answer_1')")
    assessment: Literal["Correct", "Incorrect", "Partial", "Feasible", "Unclear"] = Field(
        ..., description="Evaluator assessment of the claim"
    )


class SubcriteriaScoreWithEvidence(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Score on a scale of 0.0 to 100.0")
    evidence: List[EvidenceClaim] = Field(
        default_factory=list, description="Verifiable claims and assessment citations supporting this score"
    )


# ── LLM Qualitative Output Models ────────────────────────────────────

class TechnicalSolutionQualitativeEval(BaseModel):
    requirement_alignment: SubcriteriaScoreWithEvidence
    technical_correctness: SubcriteriaScoreWithEvidence
    architecture_quality: SubcriteriaScoreWithEvidence
    implementation_feasibility: SubcriteriaScoreWithEvidence
    edge_cases_security: SubcriteriaScoreWithEvidence


class QuestionAnswerQualitativeEval(BaseModel):
    question_index: int = Field(..., description="1-indexed question identifier")
    question_text: str = Field(..., description="The screening question text")
    candidate_answer: str = Field(..., description="The candidate's text answer")
    answer_correctness: SubcriteriaScoreWithEvidence
    technical_reasoning: SubcriteriaScoreWithEvidence
    relevance: SubcriteriaScoreWithEvidence
    depth: SubcriteriaScoreWithEvidence
    practical_examples: SubcriteriaScoreWithEvidence
    is_ai_generated: bool = Field(default=False, description="True if answer exhibits high-confidence AI generator markers or copy-paste formatting")
    ai_detection_reason: Optional[str] = Field(None, description="Specific AI generator markers or human authenticity traits identified")
    qualitative_feedback: str = Field(
        ...,
        description="Comprehensive 2-4 sentence technical evaluation and authenticity assessment of candidate response",
    )


class RequirementFulfillmentItem(BaseModel):
    requirement: str = Field(..., description="The required feature/deliverable extracted from JobPost")
    is_fulfilled: bool = Field(..., description="True if candidate's proposed milestones/solution cover this requirement")
    matched_milestone: Optional[str] = Field(None, description="Title of the matching freelancer milestone if fulfilled")
    note: Optional[str] = Field(None, description="Short justification note")


class PillarComments(BaseModel):
    technical_solution: str = Field(
        ...,
        description="Concise 1-2 sentence AI comment explaining the Solution & Delivery Methodology score, highlighting strengths or gaps."
    )
    screening_qa: str = Field(
        ...,
        description="Concise 1-2 sentence AI comment explaining Screening Q&A performance, factual accuracy, and depth (or noting missing Q&A)."
    )
    financial_value: str = Field(
        ...,
        description="Concise 1-2 sentence AI comment explaining Financial & Pricing Value relative to client budget and market rates."
    )
    milestone_scope: str = Field(
        ...,
        description="Concise 1-2 sentence AI comment explaining Milestone Scope coverage and timeline duration feasibility."
    )


class LLMQualitativeEvaluation(BaseModel):
    technical_solution: TechnicalSolutionQualitativeEval
    screening_qa: List[QuestionAnswerQualitativeEval] = Field(default_factory=list)
    requirement_fulfillment: List[RequirementFulfillmentItem] = Field(default_factory=list)
    pricing_realism: SubcriteriaScoreWithEvidence
    timeline_feasibility: SubcriteriaScoreWithEvidence
    milestone_structure: SubcriteriaScoreWithEvidence
    project_specificity: SubcriteriaScoreWithEvidence
    substance_density: SubcriteriaScoreWithEvidence
    probing_questions: List[str] = Field(
        default_factory=list, description="2-3 key questions for client to ask candidate during interview/negotiation"
    )
    pillar_comments: Optional[PillarComments] = Field(
        None, description="Concise 1-2 sentence AI comment explanations for each of the 4 evaluation pillars"
    )



# ── Deterministic Calculations Models ───────────────────────────────

class PillarScores(BaseModel):
    technical_solution: float = Field(..., description="Pillar 1 Score (35% weight)")
    screening_qa: float = Field(..., description="Pillar 2 Score (30% weight)")
    financial_value: float = Field(..., description="Pillar 3 Score (20% weight)")
    milestone_scope: float = Field(..., description="Pillar 4 Score (10% weight)")
    authenticity_fluff: float = Field(..., description="Pillar 5 Score (5% weight)")


class DeterministicCalculations(BaseModel):
    milestone_total: float = Field(..., description="Sum of freelancer's edited milestone amounts")
    proposed_budget: float = Field(..., description="Freelancer's stated proposed budget")
    is_milestone_clamped: bool = Field(..., description="True if milestone_total matches proposed_budget")
    savings_ratio: float = Field(..., ge=0.0, le=1.0, description="Savings ratio as a float between 0.0 and 1.0")
    savings_ratio_percent: float = Field(..., description="Savings percentage vs client budget max (0.0 to 100.0%)")
    timeline_variance_percent: Optional[float] = Field(None, description="Percentage variance: >0 faster, <0 slower, 0 on schedule")
    scope_completeness_percent: float = Field(..., ge=0.0, le=100.0, description="Percentage of client requirements fulfilled")
    pillar_scores: PillarScores
    overall_technical_quality_tq: float = Field(..., ge=0.0, le=100.0, description="Overall Technical Quality (0.0 to 100.0)")
    quality_interpretation_band: Literal["Exceptional", "Strong", "Acceptable", "High Risk / Poor Quality"]
    final_value_score_vs: float = Field(..., ge=0.0, le=100.0, description="Capped Value Score (0.0 to 100.0)")
    verdict_badge: Literal["top_value", "top_technical", "budget_saver", "high_risk"]


# ── Input Request Models ─────────────────────────────────────────────

class JobPostMilestoneInput(BaseModel):
    order_index: int
    title: str
    description: Optional[str] = None
    amount: float
    estimated_duration: Optional[str] = None
    deliverables: Optional[str] = None


class JobPostBaselineDto(BaseModel):
    job_id: str
    job_title: str
    job_description: str
    required_skills: List[str] = Field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    estimated_duration: Optional[str] = None
    original_milestones: List[JobPostMilestoneInput] = Field(default_factory=list)
    vetting_questions: List[str] = Field(default_factory=list)


class ProposalMilestoneInput(BaseModel):
    order_index: int
    title: str
    description: Optional[str] = None
    amount: float
    estimated_duration: Optional[str] = None
    deliverables: Optional[str] = None


class QuestionAnswerPairInput(BaseModel):
    question_index: int
    question_text: str
    candidate_answer: str


class ProposalOfferDto(BaseModel):
    proposal_id: str
    freelancer_id: str
    freelancer_name: Optional[str] = None
    proposed_budget: float
    proposed_duration: Optional[str] = None
    cover_letter: Optional[str] = None
    analysis_summary: Optional[str] = None
    solution_approach: Optional[str] = None
    edited_milestones: List[ProposalMilestoneInput] = Field(default_factory=list)
    vetting_qa_answers: List[QuestionAnswerPairInput] = Field(default_factory=list)


class CandidateJudgingRequest(BaseModel):
    job_post_baseline: JobPostBaselineDto
    candidate_proposal: ProposalOfferDto


class BatchCandidateJudgingRequest(BaseModel):
    job_post_baseline: JobPostBaselineDto
    proposals: List[ProposalOfferDto]
    batch_chunk_size: int = Field(default=1, ge=1, le=5, description="Number of proposals processed per parallel batch chunk")


# ── Full Output Response Models ──────────────────────────────────────

class CandidateJudgingResponse(BaseModel):
    proposal_id: str
    job_id: str
    llm_qualitative_evaluation: LLMQualitativeEvaluation
    deterministic_calculations: DeterministicCalculations


class BatchCandidateJudgingResponse(BaseModel):
    processed_count: int
    total_requested: int
    is_completed: bool
    judged_proposals: List[CandidateJudgingResponse]
