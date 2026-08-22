---
title: "GigBridge Admin Elo Management & Appeals"
source: "https://gigbridge.id.vn/admin/elo"
description: "Administrator portal for monitoring system-wide Elo ratings, managing tier thresholds, auditing score adjustments, and resolving Elo penalty appeals."
---

# Admin Elo Management & Appeals

The Admin Elo Management & Appeals page provides platform administrators with control over the system's Elo rating formulas, score history audits, and user appeal reviews.

---

## 1. Page Access & Sub-routes

- **Routes**:
  - `/admin/elo`: System-wide Elo overview, score distribution charts, and parameter settings.
  - `/admin/elo/history`: Master audit log of all automated and manual Elo point adjustments.
  - `/admin/elo/appeals`: Inbox of pending user penalty appeals.
  - `/admin/elo/appeals/:appealId`: Detail view for reviewing a specific Elo appeal.
- **Access**: Restricted to `Admin` role.

---

## 2. Elo Overview & Distribution Analytics (`/admin/elo`)

- **Rating Distribution**: Graphical breakdown showing user counts across Bronze, Silver, Gold, Platinum, and Diamond tiers.
- **Average Elo Score**: System-wide mean score calculation for active Freelancers and Clients.
- **System Formula Parameters**: Configuration controls for base k-factor, milestone bonus weights, and dispute penalty multipliers.

---

## 3. Penalty Appeal Review (`/admin/elo/appeals/:appealId`)

When a user submits an appeal regarding an Elo deduction:
- **Appeal Case Metadata**: User details, associated contract/dispute reference, penalty date, and deducted points.
- **User Justification**: Written explanation and supporting evidence submitted by the user.
- **Admin Verdict Actions**:
  - **Approve Appeal**: Restore deducted Elo points and log an administrative correction entry.
  - **Reject Appeal**: Maintain the Elo penalty and close the appeal case with an explanatory notice.
