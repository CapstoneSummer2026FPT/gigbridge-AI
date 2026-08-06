---
title: "GigBridge Client Dashboard"
source: "https://gigbridge.id.vn/client/dashboard"
description: "Client command center for jobs, proposals, contracts, spending, wallet funds, and talent matching."
---

# Client Dashboard

The Client Dashboard combines hiring, contract, and financial activity into a single overview. Its numbers come from the Client's current jobs, recent proposal scope, projects, contracts, wallet, and Premium status.

---

## 1. Page Access & Primary Actions

- **Route**: `/client/dashboard`
- **Access**: Clients with completed profile setup.
- **Open New Role**: Starts a project request at `/jobs/post`.
- **Premium Action**: Opens the Client Premium dashboard for active subscribers or Client pricing for non-subscribers.

The summary sentence reports open roles, pending proposals, and active contracts using the loaded account data.

---

## 2. Hiring & Proposal Overview

- **Open Roles**: Counts the Client's jobs currently in open status.
- **Proposal Pipeline**: Shows received, pending, and shortlisted proposals collected from recent roles.
- **Recent Scope Notice**: States how many recent roles were used to build the proposal pipeline.
- **Smart Matching**: Opens `/talent-matching` to find candidates for an open job; Premium eligibility is checked by that feature.

The dashboard is an overview rather than the full management interface. Detailed job and proposal actions continue on their dedicated pages.

---

## 3. Contracts & Projects

- **Active Contracts**: Lists current project engagements with their status.
- **Open Workspace**: Sends the Client to `/workspace/:contractId` for the selected active contract.
- **Completed Contracts**: Displays the completed count and links to `/contracts` for the full contract list.
- **Notifications**: Links to `/notifications` for hiring, contract, payment, and other account activity.

---

## 4. Financial Overview

The dashboard visualizes financial activity such as contract value and released contract funds. It also includes a spending chart when time-series data is available.

- **Wallet Card**: Displays the current GigCoin balance and opens `/wallet/deposit` when selected.
- **Contract Value**: Summarizes value associated with the Client's contracts.
- **Released Funds**: Reflects contract funds already released through supported milestone actions.

Values may display an empty or loading state while financial data is being retrieved; placeholders are not completed transactions.

---

## 5. Empty, Loading & Failure States

- New Clients may see zero jobs, proposals, contracts, and financial activity.
- Cards use loading placeholders until their supporting requests complete.
- The dashboard does not create a job, fund escrow, shortlist a proposal, or release payment automatically; it links to the relevant workflow.
- If a data source fails, other sections may still render from the information that loaded successfully.
