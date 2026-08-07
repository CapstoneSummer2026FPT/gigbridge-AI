---
title: "GigBridge Manage Job Screening Questions"
source: "https://gigbridge.id.vn/client/job-posts/:jobPostId/questions"
description: "Client editor for adding, editing, ordering, requiring, and removing job screening questions."
---

# Manage Job Screening Questions

This page maintains the screening-question set attached to an existing Client job post. The saved order and required flags determine how applicants encounter the questions and how answer completion is validated.

---

## 1. Page Access & Ownership

- **Route**: `/client/job-posts/:jobPostId/questions`
- **Access**: Clients with completed setup who are allowed to manage the selected job.
- **Job Context**: Loads the job and its current questions using `:jobPostId`.
- **Back Navigation**: Returns to the relevant job-management context.

Missing job ID, permission failure, or load error displays a failure state rather than an empty editable question set.

---

## 2. Question Fields

- **Question Text**: The prompt shown to the applicant.
- **Required/Optional**: Required questions must receive a valid answer in the proposal question flow.
- **Order**: Controls the sequence presented to applicants and reviewers.
- **Length Validation**: Questions exceeding the configured maximum cannot be saved.

---

## 3. Management Actions

1. Add a new question.
2. Edit existing wording.
3. Toggle whether an answer is required.
4. Move questions into the intended order.
5. Remove questions that should no longer be used.
6. Save the updated set and wait for success feedback.

Removing a question from the editor is not final until the update request succeeds.

---

## 4. Effect on Applications & Interviews

Saved questions can appear in the timed proposal-question workflow and in Client review of proposal answers. When the job has a supported AI interview definition, the interview service can use the configured question context.

Changes should be made carefully after applications exist because previously submitted answers remain proposal records and should not be assumed to rewrite themselves to match later wording.
