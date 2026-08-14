---
title: "GigBridge Create Project Request"
source: "https://gigbridge.id.vn/jobs/post"
description: "Detailed Client form for job requirements, taxonomy, skills, attachments, budget, schedule, visibility, drafts, and AI-assisted details."
---

# Create Project Request

This is the first substantive step of the Client job-posting wizard. It creates or updates a server-side draft and collects the core information later reviewed by Freelancers, proposal evaluators, and contract workflows.

---

## 1. Page Access & Draft Handling

- **Route**: `/jobs/post`
- **Access**: Clients with completed profile setup.
- **Continue Draft**: Loads existing draft job posts and lets the Client resume one.
- **Create New Draft**: Clears the active draft context and begins a separate record.
- **Autosave/Leave Protection**: Unsaved navigation can offer Save Draft, Discard, or Stay; failed autosave provides Retry.
- **Save & Exit**: Persists the current draft without publishing it.

---

## 2. Core Project Fields

- **Job Title (Required)**: Maximum 200 characters.
- **Major (Required)**: Loads the corresponding categories.
- **Category (Required)**: Loads related official skills.
- **Skills**: Add or remove suggested official skills and custom skill names. Skill entry is disabled until a category is selected.
- **Description (Required)**: Detailed project requirements entered in a large text area.
- **Attachments**: Supporting files/images displayed with filenames and removable before final submission where allowed.

Changing major or category updates dependent taxonomy selections so incompatible values are not retained.

---

## 3. Budget, Schedule & Visibility

- **Expected Budget**: Numeric GigCoin value; it can later be synchronized from the milestone total.
- **Estimated Duration**: Positive numeric value plus a supported duration unit.
- **End Date (Required)**: Target project deadline.
- **Visibility**: Controls whether the job is Public, Private, or Invite Only according to supported values.

The wizard summary shows title, budget, duration, question count, and milestone information as the draft develops.

---

## 4. AI-Assisted Detail Generation

When Instant Job Detail mode and Client Premium are available, the Client can describe the requirement to the AI service. The AI service includes support for:
- **Attachment File Extraction**: Uploaded spec documents/PDFs are parsed into text and passed into the AI prompt context to generate highly detailed Job Descriptions and accurate title suggestions.
- **Dynamic GigCoin Equivalent Calculation**: Calculates budget suggestions and GigCoin equivalents based on taxonomy, skill complexity, and scope without requiring manual budget input in the generation prompt.

Generated details open in a review modal. The Client must inspect and accept/edit them; AI generation does not bypass form validation, create escrow, or publish the job automatically.

---

## 5. Continue to Planning

Selecting the primary Continue action validates the current draft, saves it, and opens `/jobs/post/plan`. Missing required fields, taxonomy errors, attachment failures, invalid schedule values, or backend errors keep the user on the form with guidance.

The job remains a Draft until the final Review step successfully publishes it.
