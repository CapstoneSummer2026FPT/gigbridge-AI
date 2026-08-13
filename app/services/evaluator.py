from __future__ import annotations

import json
import logging
import re
from typing import List
from litellm import completion

from app.schemas.eval_schemas import EvidenceEvalResponse, ClaimDetail
from app.core.config import settings

logger = logging.getLogger("ai_server.evaluator")

EVAL_PROMPT = """
You are an expert fact-checking AI evaluator.
Your job is to analyze candidate evidence/answer text and verify every claim against the provided source context.

Source Context:
\"\"\"
{source_context}
\"\"\"

Candidate Evidence / Answer to Evaluate:
\"\"\"
{candidate_evidence}
\"\"\"

Instructions:
1. Break down the Candidate Evidence into individual factual claims.
2. For each claim, evaluate whether it is:
   - "SUPPORTED": Directly backed by fact(s) in the Source Context.
   - "PARTIAL": Partially supported, plausible, or slightly imprecise but non-contradictory.
   - "UNSUPPORTED": Contradicted by or absent from the Source Context (hallucination).
3. Return ONLY a valid JSON object matching this schema (do not wrap in markdown codeblocks if possible):

{{
  "claims": [
    {{
      "claim": "Text of the claim",
      "status": "SUPPORTED",
      "reasoning": "Brief explanation of why it is supported or unsupported",
      "source_quote": "Direct quote from source text supporting this claim"
    }}
  ]
}}
"""


class EvidenceEvaluatorService:
    """Service to evaluate truthfulness/faithfulness of candidate text against source context."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, "DEFAULT_LLM_PROVIDER", "gemini/gemini-1.5-flash")
        self.fallback_model = "gpt-4o-mini"

    def evaluate(self, source_context: str, candidate_evidence: str) -> EvidenceEvalResponse:
        """Decompose candidate evidence into claims and verify against source context."""
        if not source_context.strip() or not candidate_evidence.strip():
            return EvidenceEvalResponse(
                truth_percentage=0.0,
                total_claims=0,
                supported_claims=0,
                partial_claims=0,
                unsupported_claims=0,
                claims=[],
                annotated_html="<p class='text-gray-500 italic'>Source context or candidate evidence is empty.</p>",
            )

        prompt = EVAL_PROMPT.format(
            source_context=source_context,
            candidate_evidence=candidate_evidence
        )

        messages = [
            {"role": "system", "content": "You are a precise, objective evidence evaluation AI that outputs JSON."},
            {"role": "user", "content": prompt}
        ]

        raw_reply = ""
        try:
            response = completion(model=self.model_name, messages=messages, temperature=0.0)
            raw_reply = response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("Primary LLM (%s) failed for evidence evaluation (%s); trying fallback...", self.model_name, exc)
            try:
                response = completion(model=self.fallback_model, messages=messages, temperature=0.0)
                raw_reply = response.choices[0].message.content or ""
            except Exception as exc2:
                logger.error("Fallback LLM failed for evidence evaluation: %s", exc2)
                # Fail-soft fallback claim parsing
                return self._rule_based_fallback(source_context, candidate_evidence)

        claims_list = self._parse_claims_json(raw_reply)
        return self._build_response(candidate_evidence, claims_list)

    def _parse_claims_json(self, raw_reply: str) -> List[ClaimDetail]:
        """Parse LLM JSON response into ClaimDetail objects."""
        # Strip markdown ```json ``` wrappers if present
        clean_reply = re.sub(r"^```(?:json)?\s*", "", raw_reply.strip(), flags=re.MULTILINE)
        clean_reply = re.sub(r"```$", "", clean_reply.strip(), flags=re.MULTILINE)

        parsed_claims: List[ClaimDetail] = []
        try:
            data = json.loads(clean_reply)
            items = data.get("claims", [])
            for item in items:
                status_raw = str(item.get("status", "UNSUPPORTED")).upper()
                status = "SUPPORTED" if status_raw == "SUPPORTED" else ("PARTIAL" if status_raw == "PARTIAL" else "UNSUPPORTED")
                parsed_claims.append(
                    ClaimDetail(
                        claim=str(item.get("claim", "")),
                        status=status,
                        reasoning=str(item.get("reasoning", "")),
                        source_quote=str(item.get("source_quote", ""))
                    )
                )
        except Exception as err:
            logger.warning("Failed to parse LLM evaluation JSON: %s. Reply was:\n%s", err, raw_reply)
        return parsed_claims

    def _build_response(self, candidate_evidence: str, claims: List[ClaimDetail]) -> EvidenceEvalResponse:
        """Calculate score and build HTML visualization."""
        if not claims:
            return self._rule_based_fallback("", candidate_evidence)

        supported_count = sum(1 for c in claims if c.status == "SUPPORTED")
        partial_count = sum(1 for c in claims if c.status == "PARTIAL")
        unsupported_count = sum(1 for c in claims if c.status == "UNSUPPORTED")
        total_claims = len(claims)

        # Truth % = (Supported + 0.5 * Partial) / Total * 100
        truth_score = round(((supported_count + 0.5 * partial_count) / total_claims) * 100.0, 1)

        # Generate sentence-level highlighted HTML
        html_blocks = []
        for c in claims:
            if c.status == "SUPPORTED":
                badge = "<span style='background:#d1fae5; color:#065f46; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:12px;'>✓ VERIFIED TRUE</span>"
                border_color = "#10b981"
                bg_color = "#f0fdf4"
            elif c.status == "PARTIAL":
                badge = "<span style='background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:12px;'>⚠ PARTIAL EVIDENCE</span>"
                border_color = "#f59e0b"
                bg_color = "#fffbeb"
            else:
                badge = "<span style='background:#ffe4e6; color:#9f1239; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:12px;'>✕ UNVERIFIED / FALSE</span>"
                border_color = "#f43f5e"
                bg_color = "#fff1f2"

            quote_html = f"<div style='margin-top:6px; font-size:13px; color:#4b5563; font-style:italic;'>Quote: \"{c.source_quote}\"</div>" if c.source_quote else ""
            reasoning_html = f"<div style='margin-top:4px; font-size:13px; color:#374151;'>Reasoning: {c.reasoning}</div>"

            card_html = f"""
            <div style="margin: 10px 0; padding: 12px 16px; background-color: {bg_color}; border-left: 5px solid {border_color}; border-radius: 6px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-weight:600; font-size:15px; color:#111827;">{c.claim}</span>
                    {badge}
                </div>
                {reasoning_html}
                {quote_html}
            </div>
            """
            html_blocks.append(card_html)

        annotated_html = "".join(html_blocks)

        return EvidenceEvalResponse(
            truth_percentage=truth_score,
            total_claims=total_claims,
            supported_claims=supported_count,
            partial_claims=partial_count,
            unsupported_claims=unsupported_count,
            claims=claims,
            annotated_html=annotated_html
        )

    def _rule_based_fallback(self, source_context: str, candidate_evidence: str) -> EvidenceEvalResponse:
        """Deterministic fallback when LLM API is unavailable."""
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", candidate_evidence) if s.strip()]
        claims = []
        source_lower = source_context.lower()

        for s in sentences:
            words = set(re.findall(r"\w+", s.lower()))
            overlap = sum(1 for w in words if w in source_lower)
            ratio = overlap / max(len(words), 1)

            if ratio > 0.6:
                status = "SUPPORTED"
                reasoning = "High word overlap with source context"
            elif ratio > 0.3:
                status = "PARTIAL"
                reasoning = "Moderate word overlap with source context"
            else:
                status = "UNSUPPORTED"
                reasoning = "Low overlap with source context"

            claims.append(ClaimDetail(claim=s, status=status, reasoning=reasoning, source_quote=""))

        return self._build_response(candidate_evidence, claims)
