---
title: "GigBridge Create or Edit Proposal"
source: "https://gigbridge.id.vn/proposals/create/:jobPostId"
description: "Freelancer proposal editor for narrative approach, structured milestones, work breakdown, calculated budget, and submission."
---

# Create or Edit Proposal

The proposal editor lets an eligible Freelancer explain an approach and transform the Client's baseline plan into a detailed delivery proposal. Proposal budget and duration are derived from the milestone structure rather than entered as disconnected totals.

---

## 1. Page Access & Modes

- **Create Route**: `/proposals/create/:jobPostId`
- **Edit Route**: `/proposals/:proposalId/edit`, rendered by the same screen.
- **Access**: Freelancers with completed setup and access to the selected job/proposal.
- **Existing Proposal**: Loads saved content; editable statuses open the form, while later statuses produce a read-only notice.
- **Client Baseline**: If no proposal exists and the job has milestones, the baseline is copied into the editor for review.

---

## 2. Proposal Narrative

- **Introduction**: Relevant experience and fit for the project.
- **Proposal Approach**: Markdown-supported analysis of the problem, constraints, risks, and implementation approach.
- **Overall Deliverables**: Optional high-level output summary.
- **Assumptions**: Conditions used when estimating the work.
- **Out of Scope**: Explicit exclusions that reduce ambiguity.

Additional Details can be expanded or collapsed without losing the entered values.

---

## 3. Milestone Plan

Each milestone supports a title, positive amount, deadline, deliverables, derived duration, acceptance criteria, and nested work items. Milestone and work-item ordering is normalized when the plan changes.

Validation requires:

- At least one milestone.
- A title and amount greater than zero for every milestone.
- Required deliverables.
- Deadlines that are not in the past, follow the proposal/job date rules, and occur later than the prior milestone deadline.
- Valid work-item content where advanced breakdown is used.

---

## 4. Calculated Terms

- **Proposal Budget**: Sum of milestone amounts, shown in GigCoin.
- **Overall Duration**: Calculated from the milestone plan.
- **Work Breakdown**: Nested tasks remain associated with their parent milestone.

These calculated values help keep the proposed terms internally consistent.

---

## 5. Save & Submit

1. **Save Draft** creates or updates the proposal without sending it to the Client.
2. **Submit Proposal** first saves the latest content.
3. If the job has screening questions, GigBridge opens `/proposals/create/:jobPostId/questions` with the proposal ID.
4. If there are no questions, the proposal status is changed to Pending and the user returns to Proposals.

A proposal can be saved but fail during final status submission; the page reports this distinction so the Freelancer can retry safely.
