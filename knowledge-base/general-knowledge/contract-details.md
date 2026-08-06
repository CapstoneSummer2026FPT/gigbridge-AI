---
title: "GigBridge Contract Details"
source: "https://gigbridge.id.vn/contracts/:contractId"
description: "Participant view of contract terms, signing, milestones, and dispute state."
---

# Contract Details

**Route:** `/contracts/:contractId`

**Access:** Contract participants with completed setup.

Contract Details is the main record for an agreement between a client and freelancer. It shows the parties, project and financial context, contract status, e-sign information, milestone state, and other legal/workflow information returned by the backend.

The available actions are role- and state-dependent. They can include opening the signature workflow, managing milestones, funding or reviewing work, submitting deliverables, opening the project workspace, and raising or opening a contract report/dispute.

The page verifies participant access. A user who is not authorized to view the contract receives an access-denied state.
