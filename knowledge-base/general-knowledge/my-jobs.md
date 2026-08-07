---
title: "GigBridge My Jobs"
source: "https://gigbridge.id.vn/jobs/my-jobs"
description: "Client management center for job search, status, visibility, questions, invitations, matching, promotion, and AI interviews."
---

# My Jobs

My Jobs is the Client's operational list of draft and published project requests. It combines job-level information with controls for lifecycle status, visibility, applicants, screening, invitations, Smart Matching, Premium promotion, and AI interview configuration.

---

## 1. Page Access & Overview

- **Route**: `/jobs/my-jobs`
- **Access**: Clients with completed profile setup.
- **Create Job**: Opens `/jobs/post`.
- **Loaded Scope**: Requests up to 100 of the Client's job posts.
- **Summary Cards**: Count open, draft, closed, and unknown-status records.
- **Layout Control**: Supports regular and compact list presentation.

---

## 2. Search & Status Filters

Search matches job title, description, category, and related text loaded with each record. Status tabs include:

- All.
- Draft.
- Open.
- Closed.
- Cancelled.
- Unknown.

The page reports the filtered result count against the total loaded jobs.

---

## 3. Job Card Information

- Title, description excerpt, category, and status.
- Public, Private, Invite Only, or Locked by Admin visibility.
- GigCoin budget and proposal count.
- Current status and relevant date information.
- Featured/promotion indicator when a job promotion is active.

Unknown status or visibility data disables actions that cannot be performed safely.

---

## 4. Standard Management Actions

- **View**: Opens `/jobs/my-jobs/:jobPostId` using the Job Details screen in owner mode.
- **Questions**: Opens `/client/job-posts/:jobPostId/questions`.
- **Invite Freelancers**: Available for open jobs and launches the post-job invitation modal.
- **Publish**: Changes a Draft to Open.
- **Close**: Changes an Open job to Closed.
- **Cancel**: Available for Draft or Open jobs.
- **Visibility**: Changes eligible jobs between Public, Private, and Invite Only. Admin-locked visibility cannot be changed here.

Status and visibility are updated only after the backend confirms the request.

---

## 5. Premium Job Actions

- **Talent Matches**: Opens Smart Matching for the selected job. Non-Premium Clients are directed to Client pricing.
- **Promote**: Opens the Job Promotion Studio; active promotions are indicated on the job.
- **Enable AI Interview**: Premium action that configures an interview definition for the open job, currently requesting five questions from the service.

Premium eligibility is checked before these actions. A failed entitlement or configuration request does not activate the feature.

---

## 6. Empty & Error States

When the Client has no jobs or a filter finds none, the page offers Create Job. Loading and service errors remain distinct from an empty account. Closing or cancelling a job can disable new negotiation and application actions without deleting existing proposal or contract records.
