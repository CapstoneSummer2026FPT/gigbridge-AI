---
title: "GigBridge Contract and Escrow Flow"
source: "Current contract, wallet, and workspace implementation"
description: "Current agreement, signature, escrow, milestone, deliverable, fee, and dispute workflow."
---

# Contract and Escrow Flow

## From negotiation to contract

Proposals and messages can progress into structured negotiation and a final offer. When the platform accepts the required offer/participant actions, an eligible proposal can be used to create the contract and its milestone plan.

## Electronic signatures

Participants review contract documents through the signature workflow and sign eligible documents on the dedicated signing page. One participant's signature does not activate the entire agreement; the backend contract status is authoritative about which signatures or steps remain.

## Funding and service fees

Clients fund eligible contract escrow with spendable GigCoin. The current service-fee implementation uses a **1% rate** for the supported fee-bearing workflow actions and shows confirmation/insufficient-balance guidance before those actions. Fees and holds appear in wallet/financial records.

Funding must succeed before the interface treats money as held in escrow. A contract plan, signed document, or submitted deliverable alone does not prove that escrow is funded.

## Milestone delivery and approval

The freelancer submits the milestone outputs/evidence. The client reviews them against the stored scope, deliverables, and acceptance criteria. Approval triggers the applicable release workflow; a submission by itself does not pay the freelancer.

## Issues and disputes

Participants can raise a contract issue through the supported report/dispute flow. The case records its contract context, messages, evidence, requests, and status. Funds follow the backend's resolution outcome; the knowledge base must not promise a specific refund, payout split, or automatic-release period.
