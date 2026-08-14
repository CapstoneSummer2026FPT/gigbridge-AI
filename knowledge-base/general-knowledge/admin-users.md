---
title: "GigBridge Admin User Management"
source: "https://gigbridge.id.vn/admin/users"
description: "Administrator user directory for searching, auditing, suspending, verifying, and previewing account details."
---

# Admin User Management

The Admin User Management page allows platform administrators to search, inspect, moderate, verify, and enforce policies across all user accounts.

---

## 1. Page Access & Routes

- **Routes**: `/admin/users`, `/admin/users/:userId` (redirects to drawer/modal preview `?preview=:userId`).
- **Access**: Restricted to `Admin` role.

---

## 2. Directory Search & Filtering

- **Search Bar**: Search users by Email, Full Name, User ID, or Phone Number.
- **Role Filter**: Filter by `Client`, `Freelancer`, or `Admin`.
- **Status Filter**: `Active`, `Unverified`, `Suspended`, `Banned`.
- **Identity Verification Filter**: `Pending KYC`, `Verified`, `Rejected`.

---

## 3. User Table & Detail Drawer

For each user entry:
- **User Profile Overview**: Avatar, Name, Email, Role, Joined Date, Current Elo Score.
- **Account Actions**:
  - **View Details**: Opens full drawer displaying contact info, wallet balances, active contracts, and dispute history.
  - **Verify Identity**: Approve KYC document submissions.
  - **Suspend / Ban Account**: Restrict user access for terms of service violations.
  - **Reset Password Token**: Trigger password reset email dispatch.
  - **Adjust Elo Rating**: Override or restore Elo scores manually with an audit justification log.
