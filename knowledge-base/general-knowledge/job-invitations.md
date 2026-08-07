---
title: "GigBridge Job Invitations"
source: "https://gigbridge.id.vn/jobs/invitations"
description: "Freelancer inbox for viewing, applying to, and declining direct Client job invitations."
---

# Job Invitations

Job Invitations is the Freelancer inbox for project requests sent directly by Clients. Each record links a Client, job, optional message, and invitation status to the actions still allowed.

---

## 1. Page Access & Status Filters

- **Route**: `/jobs/invitations`
- **Access**: Completed Freelancer accounts; other roles receive an explanatory message.
- **Default Filter**: Active invitations, covering Pending and Viewed states.
- **Other Filters**: All, Applied, Declined, and Cancelled.
- **Loaded Scope**: The page requests up to 100 invitation records for the account.

Invitation status labels can include Pending, Viewed, Applied, Declined, Expired, and Cancelled.

---

## 2. Invitation Information

- Job title, description, and category.
- Official and custom skill names, with a limited set shown as tags.
- GigCoin budget range and invitation date.
- Client name or company with a link to the Client profile.
- Optional personal message supplied with the invitation.

---

## 3. View, Apply & Decline

1. **View JobPost** marks a pending invitation as viewed when possible, then opens `/jobs/:jobPostId`.
2. **Apply** marks an actionable invitation as applied and opens proposal creation with the invitation ID attached.
3. **Decline** asks for an optional reason and sends the decline request.
4. Buttons display a busy state while an invitation action is running.

Declined or cancelled invitations cannot use the normal Apply action.

---

## 4. Workflow Meaning

An invitation expresses Client interest but is not a hire, accepted offer, or contract. The Freelancer must still review the project, prepare a proposal, answer required questions, complete any applicable interview, negotiate terms, and sign a contract.

If no invitations match the selected filter, the page offers a return to Browse Jobs.
