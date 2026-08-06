---
title: "GigBridge Edit Job Post"
source: "https://gigbridge.id.vn/jobs/:id/edit"
description: "Client page for changing an existing project request."
---

# Edit Job Post

**Route:** `/jobs/:id/edit`

**Access:** Clients with a completed profile who own the job.

The page loads an existing job into an editable form. The client can update supported fields such as the project information, taxonomy, skills, budget, schedule, visibility, or description, subject to the current job status and backend validation.

Saving updates the job only after the request succeeds. Existing proposals, negotiations, or contracts remain separate records and are not silently rewritten by editing a job post.
