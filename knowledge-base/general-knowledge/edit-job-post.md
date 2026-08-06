---
title: "GigBridge Edit Job Post"
source: "https://gigbridge.id.vn/jobs/:id/edit"
description: "Client editor for updating an owned job's content, taxonomy, skills, budget, duration, deadline, and visibility."
---

# Edit Job Post

Edit Job Post loads an existing Client-owned project request into a dedicated form. It tracks unsaved changes, validates field relationships, and updates the backend only when Save Changes succeeds.

---

## 1. Page Access & Locking

- **Route**: `/jobs/:id/edit`
- **Access**: Clients with completed setup who own the selected job.
- **Loading**: Retrieves the job, professional taxonomy, and relevant skills before editing.
- **Admin Lock**: Visibility value `3` represents an administrative lock; updates, status changes, and visibility changes are disabled and the Client is told to contact support.

Missing, inaccessible, or failed job loading shows an error and a return to My Jobs.

---

## 2. Editable Fields

- **Job Title & Description**: Required project identity and requirements.
- **Major & Category**: Required taxonomy fields; changing major clears dependent category and skill selections.
- **Official & Custom Skills**: Up to 10 combined skills. Typed names matching official skills are stored using official IDs; unmatched names can remain custom.
- **Budget Range**: Optional non-negative minimum and maximum GigCoin values; maximum cannot be below minimum.
- **Project Duration**: Positive whole-number value and duration unit.
- **End Date**: Validated against the applicable date rules.
- **Visibility**: Public, Private, or Invite Only when not administratively locked.

---

## 3. Taxonomy & Skill Behavior

Selecting a major loads its categories; selecting a category loads official skills. If an existing official skill is not valid under the newly selected category, its readable name can be preserved as a custom skill rather than silently disappearing.

Skills cannot be added before a category is selected, duplicates are normalized, and the total selection limit is enforced.

---

## 4. Save & Leave Protection

1. Save validates required content, taxonomy, budget relationship, duration, date, and skills.
2. Backend validation messages are mapped to the corresponding form sections.
3. On success, the page shows Saved and returns to `/jobs/my-jobs`.
4. If the user navigates away with changes, a leave dialog can save the draft, discard it, or cancel navigation.

Discarding is treated carefully for draft records that already contain information; the system may keep an existing non-empty draft instead of deleting meaningful data.

---

## 5. Existing Hiring Records

Editing a job post updates the job record but does not silently rewrite previously submitted proposals, proposal answers, negotiations, signed contracts, or escrow transactions. Those records retain their own saved terms and statuses.
