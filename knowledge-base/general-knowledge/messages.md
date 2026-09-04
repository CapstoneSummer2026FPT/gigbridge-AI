---
title: "GigBridge Messages"
source: "https://gigbridge.id.vn/messages"
description: "Detailed communication workspace for invited-job chat, negotiation, project work, disputes, offers, files, schedules, and meetings."
---

# Messages

Messages is GigBridge's role-aware communication workspace. Conversations are grouped by relationship stage, and the active room can support plain chat, files, job context, negotiation offers, contract handoff, schedules, Google Meet, reports, or dispute navigation.

---

## 1. Page Access & Conversation Rooms

- **Route**: `/messages`
- **Access**: Clients and Freelancers with completed profile setup.
- **Invited**: Communication connected to a direct job invitation.
- **Negotiation**: Offer and terms discussion before contract creation.
- **Workspace**: Communication attached to an active contract workspace.
- **Dispute**: Conversation and system events connected to an escalated issue.

Each room displays conversations, last-message information, time, and unread count. Selecting a conversation loads its message history and job/participant context.

---

## 2. Messages & Files

- Send text with Enter behavior and a dedicated Send action.
- Add an emoji shortcut to the current draft.
- Attach supported files; image attachments receive previews where available.
- Pending and failed outgoing messages are visibly distinguished; failed messages are not presented as saved.
- The information panel lists shared attachments with filename, size, preview type, and download link.
- Profile and job links open the corresponding details pages.

---

## 3. Negotiation & Final Offers

Clients can request negotiation from an invited room when the job remains open. In a negotiation room, structured final offers can include milestone terms and are shown as offer messages.

- Only the latest offer is treated as the current actionable version.
- Offer state can be idle, pending, agreed, declined, or superseded.
- Accepting may check wallet/service-fee conditions before confirmation.
- An agreed deal displays a contract-ready banner and an Open Contract action for both parties.
- If the job closes, final-offer and negotiation responses are disabled.

Agreement in Messages prepares the contract workflow; it is not a signed contract by itself.

---

## 4. Scheduling & Vietnam Time

Clients can create a schedule with title, date/time, optional details, and optional email invitation. Schedule times are displayed in **Asia/Ho_Chi_Minh** and labeled Vietnam Time (ICT).

- Eligible users can edit or cancel before the cutoff.
- Participants can accept, reject, or propose a different time according to the current agreement state.
- Reschedule requests are limited and show remaining requests.
- Near-midnight schedules require explicit acknowledgement because the cancellation window may be short.
- Superseded schedule messages point to the latest schedule card.

---

## 5. Google Meet & Video Call Scheduling (ggmeet, gmeet)

When creating a schedule in an Invited or Negotiation room, the Client can request a Google Meet (ggmeet, gmeet) link after connecting a Google account in Settings. The interface checks connection status, offers connect/reconnect, shows pending meeting creation, allows retry after eligible failures, and reveals the join link when ready for both Client and Freelancer.

Meet links open in a new browser tab. Selecting Add Google Meet without a valid Google Workspace connection prompts the user to connect Google Meet first.

---

## 6. Conversation & Project Controls

- Open the related workspace from workspace rooms.
- View participant profile and job information in the side panel.
- Block or unblock contact where the current conversation permits it.
- Open contract-report details from system messages.
- Navigate to a created dispute from the appropriate workspace/dispute context.

Blocking affects communication controls; it does not cancel a job, proposal, contract, escrow, or dispute record.

---

## 7. Empty & Error States

With no selected conversation, the page explains how to begin from an invitation or negotiation. Schedule conflicts, failed sends, unavailable reports, offer failures, and meeting errors remain visible so users can retry or inspect the underlying workflow safely.
