---
title: "GigBridge User-Facing Page Directory"
source: "Gigbridge_frontend/src/app/router.tsx"
description: "Current route directory for public, client, freelancer, and shared GigBridge pages."
---

# User-Facing Page Directory

This directory reflects the current application router. Admin-only, legacy redirect, OAuth callback, and 404 routes are excluded. Detailed behavior is documented in the page-specific files in this folder.

## Public and account pages

* `/` — Homepage
* `/about`, `/careers`, `/faq`, `/press-kit`, `/guide` — Public company and help pages
* `/policies`, `/terms`, `/privacy` — Server-managed policy viewer routes
* `/auth/login`, `/auth/signup`, `/auth/forgot-password`, `/auth/reset-password` — Authentication and recovery
* `/onboarding/profile-setup` — Required role-specific profile onboarding

## Client and freelancer hubs

* `/client/dashboard`, `/freelancer/dashboard` — Role dashboards
* `/profile/client/:id`, `/profile/freelancer/:id` — Participant profiles
* `/settings`, `/notifications` — Account settings and notification inbox
* `/premium/client`, `/premium/client/pricing` — Client Premium hub and plans
* `/premium/freelancer`, `/premium/freelancer/pricing` — Freelancer Premium hub and plans
* `/premium/freelancer/points`, `/premium/freelancer/rank-protection`, `/premium/freelancer/promotions`, `/premium/freelancer/history` — Freelancer Premium tabs

## Jobs and hiring

* `/jobs/post/guide`, `/jobs/post`, `/jobs/post/plan`, `/jobs/post/review` — Client project-request flow
* `/jobs/post/contract`, `/jobs/post/esign` — Job contract and e-sign preparation
* `/jobs/browse`, `/jobs/saved`, `/jobs/invitations`, `/jobs/my-jobs` — Discovery and management lists
* `/jobs/:id`, `/jobs/:id/edit` — Job details and client editing
* `/client/job-posts/:jobPostId/questions` — Client screening-question management
* `/proposals` — Role-aware proposal inbox
* `/proposals/create/:jobPostId`, `/proposals/:proposalId/edit` — Proposal create/edit
* `/proposals/create/:jobPostId/questions`, `/proposals/:proposalId/answers` — Screening answers
* `/talent-matching` — Client freelancer directory, saved talent, and Premium smart matching
* `/ai-interview/:jobPostId` — Voice-led application interview

## Contracts and delivery

* `/contracts`, `/contracts/esign` — Contract and e-sign lists
* `/contracts/create/:proposalId`, `/contracts/:contractId` — Create/view contract
* `/contracts/:contractId/sign`, `/contracts/:contractId/documents/:documentId/sign` — Signing flow
* `/contracts/:contractId/milestones` — Milestone management
* `/contracts/:contractId/milestones/:milestoneId/approve` — Client approval
* `/contracts/:contractId/deliverables/:milestoneId` — Freelancer delivery
* `/contracts/:contractId/disputes/:disputeId` — Participant dispute case
* `/projects`, `/workspace/:contractId`, `/messages` — Projects, workspace, and communications
* `/reviews`, `/reviews/create` — Review history and creation

## Wallet and analytics

* `/wallet/deposit` — PayOS GigCoin top-up
* `/wallet/history` — Wallet transaction ledger
* `/wallet/withdrawals` — Eligible earned-GigCoin payout requests
* `/buy-gigcoin` — Package-selection/demo page; real top-ups use Wallet Deposit
* `/financial-overview` — Role-aware payments or earnings analytics

The former `/market-insights` route and earlier admin routes such as `/admin/cheating` are not part of the current router.
