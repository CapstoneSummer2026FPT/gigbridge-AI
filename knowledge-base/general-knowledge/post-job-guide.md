---
title: "GigBridge Post a Job Guide"
source: "https://gigbridge.id.vn/jobs/post/guide"
description: "Client entry page for choosing manual job creation or Premium AI-assisted Instant Job Detail."
---

# Post a Job Guide

The Post a Job Guide is the entry point to project-request creation. It distinguishes the standard manual workflow from Instant Job Detail, which uses AI to propose editable project information for an eligible Client Premium account.

---

## 1. Page Access & Purpose

- **Route**: `/jobs/post/guide`
- **Access**: Clients with completed profile setup.
- **Next Route**: Both creation methods continue to `/jobs/post` with mode information in navigation state.
- **Premium Check**: The page loads the Client subscription state before allowing AI mode.

---

## 2. Instant Job Detail

The highlighted AI option is intended to turn a plain-language requirement into proposed job fields. Its card shows whether Premium is active, still loading, unavailable, or required.

- Active Premium Clients can enter job creation in Instant mode.
- Standard Clients are redirected to `/premium/client/pricing`.
- If Premium status cannot be confirmed, selecting the option retries the entitlement request rather than assuming access.

AI-generated content remains a draft and must be reviewed for accuracy, scope, taxonomy, skills, budget, and schedule.

---

## 3. Manual Creation

Manual mode opens the same job form without requiring Premium. The Client directly enters the title, major, category, skills, description, budget, duration, deadline, attachments, visibility, milestones, and optional interview questions.

---

## 4. Information to Prepare

- A clear project outcome and requirement description.
- The relevant professional major, category, and required skills.
- A realistic GigCoin budget and delivery timeline.
- Measurable milestone outcomes and acceptance criteria.
- Screening questions that help distinguish suitable applicants.

Choosing a mode does not publish a job. Publication happens only after the draft, plan, and review workflow succeeds.
