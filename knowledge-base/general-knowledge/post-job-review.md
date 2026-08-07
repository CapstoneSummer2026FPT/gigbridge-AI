---
title: "GigBridge Job Post Review"
source: "https://gigbridge.id.vn/jobs/post/review"
description: "Final Client verification of project details, budget, timeline, milestones, attachments, questions, and visibility before publication."
---

# Job Post Review

The Review step assembles every part of the current job draft into a final read-only summary. It gives the Client a last opportunity to find inconsistent scope, taxonomy, budget, timing, milestones, or questions before the publish request is sent.

---

## 1. Page Access & Draft State

- **Route**: `/jobs/post/review`
- **Access**: Clients with completed setup and a job draft passed from the wizard.
- **Missing State**: Redirects to `/jobs/post` if no job ID or draft data is available.
- **Navigation**: Edit/Back returns to the relevant wizard step; Save & Exit keeps the job as a draft.

---

## 2. Details Reviewed

- Job title, major, category, and full description.
- Official and custom skills.
- Uploaded attachment previews and filenames.
- Expected or milestone-derived GigCoin budget.
- Estimated duration, end date, and Public/Private/Invite Only visibility.
- Baseline milestones with amount, duration, deadline, description, deliverables, acceptance criteria, and work breakdown.
- Interview questions with required or optional labels.

---

## 3. Consistency Checks

The page compares milestone total with expected budget and milestone duration with the stated project duration. Validation errors can direct focus to the relevant section rather than sending an invalid publish request.

Clients should correct mismatches that could confuse applicants even when a field is technically optional.

---

## 4. Publishing

1. Select Publish after reviewing all sections.
2. The wizard saves the latest draft data and requests the Open/published state.
3. Successful publication makes the job eligible for its configured visibility and normal application rules.
4. A failed request keeps the draft available for correction or retry.

Publication does not create a signed contract or escrow deposit. Those occur later after proposal selection and agreement.

---

## 5. Safe Interpretation

Only a success response confirms publication. Being able to view this page, pressing Publish, or having complete-looking local fields is not enough if the backend returns a validation or service error.
