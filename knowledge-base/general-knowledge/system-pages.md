---
title: "GigBridge System Pages"
source: "Codebase Audit /router.tsx"
description: "Master catalog mapping all functional screens and pages in the GigBridge system by user roles."
---

# Master Page Directory

The GigBridge web application contains **60 unique screens** serving different roles (Guests, Onboarded Users, Freelancers, Clients, and Administrators). Each page has specific routes and functional responsibilities.

---

## 1. Guest & Public Screens (No Auth Required)

- **Homepage (`/`)**: Core landing screen showcasing escrows, digital signing, matchmaking, and workspace features.
- **About Page (`/about`)**: Insights on the company mission, what the platform offers, and target users.
- **Careers Page (`/careers`)**: Job departments (Engineering, AI, Security) and benefit perks.
- **FAQ Page (`/faq`)**: Interactive list answering questions on fees, contracts, payments, and account security.
- **User Guide (`/guide`)**: Step-by-step onboarding walkthroughs for freelancers and clients.
- **Press Kit Page (`/press-kit`)**: Media guidelines, logo links, and hex codes for official brand colors.
- **Market Insights (`/market-insights`)**: Live trends on active developer niches (left empty).
- **Login (`/auth/login`)**: Sign-in portal using email and password.
- **Signup (`/auth/signup`)**: Platform registration where users choose either "Client" or "Freelancer" role.
- **Forgot Password (`/auth/forgot-password`)**: Portal to request a password reset email token.
- **Reset Password (`/auth/reset-password` or `/api/Auth/reset-password`)**: Form to input and save a new account password using verification tokens.

---

## 2. Onboarding (Auth Required)

- **Profile Setup (`/onboarding/profile-setup`)**: Mandatory interactive wizard to populate skills, title, bio, location, and rates.

---

## 3. Freelancer Screens (Freelancer Role Required)

- **Freelancer Dashboard (`/freelancer/dashboard`)**: Home screen summarizing bid stats, active invitations, active milestones, and profile score.
- **Browse Jobs (`/jobs/browse`)**: Grid view to search, filter by skill, or review AI match recommendations.
- **Saved Jobs (`/jobs/saved`)**: List of bookmarked job opportunities.
- **Job Detail (`/jobs/:id`)**: Displays full client description, required skills, budget, and application buttons.
- **Proposals Inbox (`/proposals`)**: Tracks status of submitted bids (Pending, Shortlisted, Hired).
- **Create Proposal (`/proposals/create/:jobPostId` or `/jobs/:jobPostId/apply`)**: Application form to input proposed milestone price, timeline, and cover letter (AI-generated optional).
- **Edit Proposal (`/proposals/:proposalId/edit`)**: Adjust bids before the client reviews them.
- **Answer Screening Questions (`/proposals/create/:jobPostId/questions`)**: Form to answer client-defined screening questions.
- **Freelancer Profile (`/profile/freelancer/:id`)**: Public profile page showing freelancer ratings, portfolio list, bio, and completed contracts.
- **Edit Profile (`/profile/freelancer/:id/edit`)**: Form to update personal details, hourly rate, and profile picture.
- **Manage Content (`/profile/manage-content`)**: Specialized editor to modify portfolio URLs, skill list, and upload resumes.
- **Freelancer Premium Dashboard (`/premium/freelancer` or `/premium/freelancer/points` / `/premium/freelancer/rank-protection` / `/premium/freelancer/promotions` / `/premium/freelancer/history`)**: Manage premium points, buy promotions, review points history, and view active rank protection.
- **Freelancer Pricing (`/premium/freelancer/pricing`)**: Purchase points/premium tiers using GigCoins.

---

## 4. Client Screens (Client Role Required)

- **Client Dashboard (`/client/dashboard`)**: Displays active hiring posts, matching candidates, and active contracts.
- **Post Job Guide (`/jobs/post/guide`)**: Contextual instructions advising clients how to structure job posts to attract talent.
- **Post Job Form (`/jobs/post`)**: Input details for a new job post (title, description, budget, required skills, and screening questions).
- **Create Post Job Contract (`/jobs/post/contract`)**: Link standard contract templates to the job post.
- **Create Post Job E-Sign (`/jobs/post/esign` or `/jobs/post/contract/esign`)**: Configure e-sign policies and authorization rules.
- **Edit Job Post (`/jobs/:id/edit`)**: Modify details of an open position.
- **Manage Job Post Questions (`/client/job-posts/:jobPostId/questions`)**: Define or edit screening questions.
- **Proposals Review (`/proposals`)**: Workspace listing all incoming applications.
- **View Proposal Answers (`/proposals/:proposalId/answers`)**: Shows answers submitted by freelancers to screening questions.

---

## 5. Contract, E-Sign & Escrow Screens (Shared/Unified Router)

- **Contract List (`/contracts`)**: Lists active and past contracts. Freelancers see their contracts, while clients see their contractor agreements.
- **E-Sign Contracts Repository (`/contracts/esign`)**: Repository of electronic signing templates.
- **Create Contract (`/contracts/create/:proposalId`)**: Pre-populates fields based on the proposal to set up milestones and sign rules.
- **View Contract (`/contracts/:contractId`)**: Visual page showing legal clauses, total budget, freelancer information, and milestone list.
- **Sign Contract Workflow (`/contracts/:contractId/sign`)**: Initiates verification before signing.
- **Esign Pad (`/contracts/:contractId/documents/:documentId/sign`)**: Sign screen containing a HTML5 canvas drawing pad for digital signatures.
- **Manage Milestones (`/contracts/:contractId/milestones`)**: Detail view of milestone status (Not Started, Funded, Pending Approval, Released).
- **Approve Milestone (`/contracts/:contractId/milestones/:milestoneId/approve`)**: Client page to authorize milestone fund release.
- **Submit Deliverable (`/contracts/:contractId/deliverables/:milestoneId`)**: Freelancer portal to upload deliverable files or code URLs.
- **Create Dispute (`/contracts/:contractId/disputes/create`)**: Dispute filing form to log complaints, explain issue details, and attach proof files.

---

## 6. Workspace & Collaboration Screens

- **Projects List (`/projects`)**: Grid list of all active workspaces.
- **Project Workspace (`/workspace/:contractId`)**: Dedicated interface containing Kanban task boards, code file sharing repositories, and messaging feeds.
- **Messages (`/messages`)**: Communication inbox for active chat negotiations.

---

## 7. AI & Market Features

- **AI Interview (`/ai-interview`)**: Portal conducting mock video/voice interviews utilizing ElevenLabs Text-to-Speech and Whisper Speech-to-Text.
- **Talent Matching (`/talent-matching`)**: Advanced candidate search page showing matching recommendations ranked by vector similarity.

---

## 8. Wallet, Payments & Settings

- **Settings (`/settings`)**: Interface to toggle notifications, change language preferences, or enable Two-Factor Authentication.
- **Wallet Deposit (`/wallet/deposit`)**: Deposit VND via local cards or bank transfers.
- **Mock Checkout (`/wallet/mock-checkout`)**: Local sandbox card terminal simulator.
- **Wallet History (`/wallet/history`)**: Chronological transaction statements.
- **Upload Payment Proof (`/wallet/payment-proof/:transactionId`)**: Receipt proof upload form for manual deposit approval.
- **Withdrawals (`/wallet/withdrawals`)**: Initiate early payout or manual bank withdrawals.
- **Buy Gigcoin (`/buy-gigcoin`)**: Purchase token credits.
- **Subscription Management (`/subscription`)**: View active plan and switch tiers.
- **Financial Overview (`/financial-overview`)**: Profit/loss dashboards.

---

## 9. Admin Panel Screens (Admin Role Required)

- **Admin Dashboard (`/admin`)**: Summary of system metrics (total commissions, active users, escrow status).
- **Admin Users (`/admin/users`)**: Search and moderate user profiles (suspend, ban, verify).
- **Admin Jobs (`/admin/jobs`)**: Review and audit public postings.
- **Admin Contracts (`/admin/contracts` or `/admin/contract-audit`)**: Tracks contract audit trails.
- **Admin Assets (`/admin/assets`)**: Manage platform images, icons, and static assets.
- **Admin Contract Templates (`/admin/contract-templates`)**: Standardize legal clauses.
- **Admin FAQ Management (`/admin/faq-management`)**: Edit and publish questions and answers.
- **Admin Ads Packages (`/admin/ads-packages`)**: Set rates for promotions.
- **Admin Dispute Management (`/admin/disputes`)**: Admin dashboard to audit deliverables, review workspace chat history, and distribute escrow funds.
- **Admin Reports (`/admin/reports`)**: Access analytics.
- **Admin Feedback (`/admin/feedback`)**: Review moderation.
- **Admin System Tracking (`/admin/system-tracking`)**: Logging backend API errors and performance metrics.
- **Admin Revenue (`/admin/revenue` or `/admin/system-finance`)**: Statement of platform commission income.
- **Admin Withdrawals (`/admin/withdrawals`)**: Review and approve user bank withdrawal requests.
- **Admin Cheating (`/admin/cheating`)**: Monitor candidate browser tab-out logs during AI interviews.
