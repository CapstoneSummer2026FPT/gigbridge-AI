---
title: "GigBridge Criteria AI Judgment & Milestone Matrix"
source: "https://gigbridge.id.vn/proposals"
description: "Documentation on deterministic 4-pillar Criteria AI Judgment evaluation, Technical Quality score, Value Score, criteria judgment badges, and side-by-side milestone comparison matrix."
---

# Criteria AI Judgment & Milestone Comparison Matrix

GigBridge provides recruiters and clients with Criteria AI Judgment evaluation tools integrated directly into proposal detail views and candidate comparison drawers.

---

## 1. Criteria AI Judgment System

The Criteria AI Judgment card synthesizes candidate proposal quality into quantitative scores, criteria judgment badges, mathematical formula tooltips, and executive decision summaries.

### Deterministic 4-Pillar Criteria AI Judgment System
1. **Technical Solution & Delivery Methodology (35% Weight)**
   - Evaluates introduction alignment (25%), problem analysis (25%), proposed architecture (25%), deliverables (15%), and scope boundaries (10%).
2. **Screening Q&A Accuracy & Reasoning (30% Weight)**
   - Evaluates candidate answers to screening questions across correctness (40%), technical reasoning (25%), relevance (15%), depth (10%), and practical examples (10%).
3. **Financial & Pricing Value (20% Weight)**
   - Combines budget savings ratio relative to maximum client budget cap (50%) and AI pricing realism relative to scope complexity (50%).
4. **Milestone Scope & Timeline Feasibility (15% Weight)**
   - Evaluates requirement scope coverage (40%), milestone phase structure (30%), and velocity realism (30%).

### Metrics & Formulas
- **Technical Quality Score (TQ)**:
  $$\text{TQ} = 0.35 \times \text{Tech} + 0.30 \times \text{Q\&A} + 0.20 \times \text{Financial} + 0.15 \times \text{Scope}$$
- **Value Score (VS)**:
  $$\text{VS} = \min(100.0,\, \text{TQ} \times (1 + 0.5 \times \text{Savings Ratio}))$$
- **Quality Bands**: `Exceptional` ($\text{TQ} \ge 90$), `Strong` ($\text{TQ} \ge 75$), `Acceptable` ($\text{TQ} \ge 60$), `High Risk` ($\text{TQ} < 60$).
- **Criteria AI Judgment Badges**:
  - 🔥 `Top Value Candidate` (High quality score + budget savings)
  - 🤝 `Qualified Match` (Solid technical & scope alignment)
  - ⚠️ `High Risk Candidate` (Low TQ score or missed Q&A)

---

## 2. AI Side-by-Side Milestone Comparison Matrix

The Side-by-Side Milestone Comparison Matrix (`AISideBySideMilestoneMatrix`) provides a comparative breakdown:
- **Client Baseline Plan**: Baseline milestones, budget caps, target deadlines, and required deliverables.
- **Freelancer Proposed Plan**: Proposed milestone sequence, individual milestone prices, estimated durations, and detailed deliverable descriptions.
- **AI Variance Analysis**: Compares price variance per milestone, duration acceleration/delays, requirement scope coverage %, and risk warnings.
