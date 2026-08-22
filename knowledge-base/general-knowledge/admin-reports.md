---
title: "GigBridge Admin Violation Reports"
source: "https://gigbridge.id.vn/admin/reports"
description: "Administrator report queue for handling user account complaints, job post violations, and contract misconduct reports."
---

# Admin Violation Reports

The Admin Violation Reports page enables administrators to manage user reports filed regarding inappropriate conduct, off-platform payment solicitation, spam, identity fraud, or contract violations.

---

## 1. Page Access & Routes

- **Routes**: `/admin/reports`, `/admin/reports/accounts/:reportId`, `/admin/reports/contracts/:reportId`.
- **Access**: Restricted to `Admin` role.

---

## 2. Report Classification & Filter Tabs

- **Account Reports (`/admin/reports/accounts`)**: Complaints filed against user accounts (harassment, fake credentials, spam).
- **Contract Reports (`/admin/reports/contracts`)**: Violations occurring within contracts or milestone communications.
- **Job Post Reports**: Content policy violations on public job postings.

---

## 3. Investigation & Moderation Actions

- **Review Evidence**: Examine reporter statements, screenshots, chat message logs, or profile links.
- **Dismiss Report**: Mark report as unfounded or invalid.
- **Issue Warning**: Send formal policy warning to the reported user account.
- **Account Action**: Apply temporary suspension, permanent ban, or Elo penalty.
- **Report Status Lifecycle**: `Open` -> `Under Investigation` -> `Action Taken` / `Dismissed`.
