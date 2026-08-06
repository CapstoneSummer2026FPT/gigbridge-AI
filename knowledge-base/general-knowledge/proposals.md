---
title: "GigBridge Proposals Inbox"
source: "https://gigbridge.id.vn/proposals"
description: "Role-aware workspace for Freelancer proposal tracking and Client candidate evaluation, shortlisting, rejection, and negotiation."
---

# Proposals Inbox

The Proposals route selects a different workspace according to the signed-in role. Freelancers manage submissions they created; Clients compare proposals received for their jobs and decide which candidates advance.

---

## 1. Page Access & Role Selection

- **Route**: `/proposals`
- **Access**: Clients and Freelancers with completed profile setup.
- **Freelancer View**: Submitted proposal list and selected-proposal details.
- **Client View**: Job-scoped candidate list, evaluation drawer, and hiring actions.
- **Job Query**: Clients may enter with `?job=:jobPostId` to focus on a specific role.

---

## 2. Freelancer Proposal Management

- Filters proposals by All, Draft, Pending, Shortlisted, Accepted, Rejected, or Withdrawn status.
- Loads paginated results with 10 proposals per page and provides numbered navigation.
- Shows job, current status, submitted terms, and selected proposal details.
- Allows Continue Editing only while the status helper permits changes.
- Allows withdrawal only for Pending proposals.
- Opens saved question answers where status allows.
- Opens the AI Interview for eligible Pending, Shortlisted, or Accepted proposals when an interview definition exists.
- Opens Messages after an Accepted proposal.

Withdrawing changes the proposal to Withdrawn; it does not delete the historical submission.

---

## 3. Client Evaluation Workspace

Clients can filter/sort proposals, select a job, paginate candidates, and open a detailed proposal panel. The panel can include:

- Freelancer identity and proposal status.
- Proposed GigCoin budget and duration.
- Introduction, approach, deliverables, assumptions, and out-of-scope notes.
- Milestone outcomes, deadlines, acceptance criteria, and work items.
- Screening-question answers.
- AI interview/evaluation report and per-question feedback when available.

Legacy proposals without structured milestone plans are identified rather than displayed as complete modern plans.

---

## 4. Client Hiring Actions

- **Shortlist**: Marks an eligible proposal for closer review.
- **Reject**: Requires confirmation and changes the proposal status.
- **Start Negotiation**: Accepts an eligible proposal into the negotiation flow and opens Messages.
- **Open Negotiation**: Available for a proposal already in the Accepted state.
- **Evaluate with AI**: Requests an evaluation when answer content exists but no report is available.

These actions are disabled when the job is no longer open for negotiation or the proposal status does not allow the transition.

---

## 5. Interpretation & Errors

Shortlisted is not hired, Accepted here leads to negotiation, and an agreed final offer still requires the contract workflow. Loading, evaluation, and status-update errors are shown without pretending the requested transition succeeded.
