---
title: "GigBridge Saved Jobs"
source: "https://gigbridge.id.vn/jobs/saved"
description: "Freelancer bookmark list for revisiting and removing saved GigBridge jobs."
---

# Saved Jobs

Saved Jobs collects project requests bookmarked by the current Freelancer. It is a personal shortlist for later review, not an application queue or guarantee that a posting remains open.

---

## 1. Page Access & Loading

- **Route**: `/jobs/saved`
- **Access**: Authenticated users; the save workflow is intended for Freelancers.
- **Data Source**: Loads the current account's saved-job records from the saved-job service.
- **Identifiers**: Supports the saved record's job-post identifier variants when opening or removing an item.

---

## 2. Information Shown

Each saved card can display the job title, description, category, skills, GigCoin budget, location/work type, date information, and current information returned with the bookmark record.

Because the underlying project may change after it was saved, open Job Details to verify status, deadline, budget, questions, and eligibility before applying.

---

## 3. Available Actions

- **Open Job**: Navigates to `/jobs/:id` for the full current project request.
- **Remove Bookmark**: Calls the unsave endpoint and removes the card after success.
- **Browse Jobs**: Returns to `/jobs/browse` to find more opportunities.

A failed removal leaves the bookmark in place and shows an error rather than silently treating it as deleted.

---

## 4. Important Limitations

- A saved job does not create a draft proposal.
- It does not extend a deadline or prevent the Client from closing or cancelling the post.
- It does not mark an invitation as accepted.
- An empty state means the account currently has no loaded saved-job records; users can begin from Browse Jobs.
