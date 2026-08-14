---
title: "GigBridge Admin Job Posting Audit"
source: "https://gigbridge.id.vn/admin/jobs"
description: "Administrator job portal for auditing client postings, enforcing content policies, reviewing AI-generated job posts, and removing violating listings."
---

# Admin Job Posting Audit

The Admin Job Posting Audit page allows administrators to inspect all public and private job posts created on the platform, ensuring compliance with community standards and legal regulations.

---

## 1. Page Access & Filters

- **Route**: `/admin/jobs`
- **Access**: Restricted to `Admin` role.
- **Filters**:
  - **Status**: `Draft`, `Open`, `In Progress`, `Completed`, `Cancelled`, `Flagged`.
  - **Category / Major**: Filter by developer category or skill domain.
  - **Posting Source**: Standard Client Form vs AI Job Post Generator.

---

## 2. Job Listing Information

- **Job Title & ID**: Unique posting identifier and header.
- **Client Account**: Link to client profile and posting history.
- **Budget & Milestones**: Total budget value in GigCoins and milestone breakdown.
- **AI Generation Flag**: Indicates if job specifications were generated using AI assistants.
- **Content Moderation Status**: Flagged keywords, prohibited requirements, or reported content status.

---

## 3. Moderation Actions

- **Review Job Detail**: Inspect description, attachments, screening questions, and linked contracts.
- **Flag for Review**: Temporarily hide job from public browse grid pending client clarification.
- **Take Down / Delete Listing**: Remove job postings that violate platform safety, copyright, or illegal work policies.
- **Notify Client**: Send automated compliance notification warning to the client.
