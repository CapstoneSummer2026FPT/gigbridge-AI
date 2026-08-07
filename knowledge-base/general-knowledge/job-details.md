---
title: "GigBridge Job Details"
source: "https://gigbridge.id.vn/jobs/:id"
description: "Complete project-request view for scope, Client information, milestones, eligibility, applications, and owner management."
---

# Job Details

Job Details is the authoritative user-facing view of a selected project request. It presents the current backend record and changes its actions according to viewer role, ownership, job status, existing proposal, and AI-interview configuration.

---

## 1. Page Access & Header

- **Route**: `/jobs/:id`
- **Access**: Authenticated users.
- **Back Destination**: Clients managing their own job return to My Jobs; other users return to Browse Jobs.
- **Header Data**: Status, category or badges, budget range, proposal count, and AI Interview label where enabled.
- **Share**: Copies or shares the current job URL using the available browser capability.

Freelancers can also save or unsave the job from this page.

---

## 2. Project Information

- **Description & Requirements**: Full requirement text supplied by the Client.
- **Required Skills**: Official and relevant skill names attached to the job.
- **Budget**: Minimum and maximum values shown in GigCoin.
- **Deadline & Work Context**: Displays the supplied deadline or a flexible state and remote/on-site information where available.
- **Proposal Count**: Number of proposals reported for the job.
- **Baseline Milestone Plan**: Read-only outcomes, amounts, duration/deadline, deliverables, acceptance criteria, and work items configured by the Client.

The baseline plan helps applicants prepare their proposal; it is not funded escrow.

---

## 3. Client Information

Freelancer viewers receive an About Client card containing available name, avatar, company, industry, location, and a link to `/profile/client/:id`.

Client profile information helps with evaluation but does not replace the job scope, eventual final offer, or signed contract.

---

## 4. Freelancer Application States

- **No Existing Proposal**: Eligible open jobs show an Apply action; AI-enabled jobs label the action as applying with an AI interview.
- **Existing Draft**: Can show Continue Editing when the proposal status permits changes.
- **Pending Proposal**: May allow withdrawal and viewing submitted answers according to status rules.
- **Closed or Ineligible Job**: Explains that proposals are no longer accepted.
- **Status Check Failure**: Shows that proposal status could not be verified and asks the user to retry rather than risking a duplicate application.

Applying opens the proposal workflow; it does not immediately hire the Freelancer.

---

## 5. Client Owner Actions

- **Edit Job**: Opens `/jobs/:id/edit`, unless the job is locked by an administrative visibility state.
- **Review Proposals**: Opens `/proposals?job=:id` and shows the current proposal count.
- **Job Management**: Additional status, visibility, invitation, question, matching, and Premium controls are available from My Jobs.

---

## 6. Similar Jobs & Errors

Non-owner viewers may receive similar open-job cards with budget and work context. Loading, missing-job, permission, and service errors produce dedicated states; a missing page must not be interpreted as an open opportunity.
