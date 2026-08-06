---
title: "GigBridge Create E-Sign Contract"
source: "https://gigbridge.id.vn/contracts/create/:proposalId"
description: "Create a contract from an accepted or eligible proposal."
---

# Create E-Sign Contract

**Route:** `/contracts/create/:proposalId`

**Access:** Signed-in users with completed setup and permission for the proposal.

The page creates a contract using proposal, job, participant, price, and milestone context. The creator reviews the generated agreement information and supplies any required contract/document details before saving.

Creating the record begins the contract workflow; it does not mean both parties have signed or that milestone funds have been placed in escrow. Those steps occur through the signing and milestone pages after successful contract creation.
