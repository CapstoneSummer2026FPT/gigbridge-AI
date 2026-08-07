---
title: "GigBridge My Reviews"
source: "https://gigbridge.id.vn/reviews"
description: "Received and sent review history for clients and freelancers."
---

# My Reviews

My Reviews is the signed-in user's history of marketplace feedback. It separates reviews received from reviews sent and preserves the project, counterparty, component scores, comment, and moderation state of each entry.

---

## 1. Page Organization

- **Route**: `/reviews`
- **Tabs**: `Received` and `Sent`.
- **Pagination**: Ten entries per page.
- **Context**: Each card links the feedback to its project and the other participant where that profile is available.

Loading, empty, and failed-request states are displayed independently. Hidden/moderated information follows backend visibility rather than being reconstructed by the browser.

---

## 2. Rating Details

Each review shows its overall score, communication, quality, timeliness, optional comment, and date. Labels reflect who was evaluated:

- A freelancer's quality/timeliness mean **work quality** and **on-time delivery**.
- A client's quality/timeliness mean **requirement clarity** and **approval/payment timeliness**.

Reviews are not anonymous in the current form, so the interface does not provide a working anonymous-profile link.

---

## 3. Reporting a Review

Users can report an eligible review they received. Report categories are Spam, Fraud, Inappropriate, Harassment, and Other. A reason of at least 10 characters is required. The report action is hidden when an open report already exists or the review has already been hidden.

Submitting a report creates a moderation request; it does not immediately delete the review. The modal remains locked while the request is processing and displays any failure returned by the service.

---

## 4. Reviews vs. Contract Issues

Reviews describe participant performance after eligible work and are normally one per participant per contract. Payment, scope, delivery, or active collaboration problems should be handled through workspace reports and disputes. This separation keeps public/reputation feedback from being mistaken for a request to change contract or wallet state.
