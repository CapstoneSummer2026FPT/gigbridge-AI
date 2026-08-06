---
title: "GigBridge Terms of Service"
source: "https://gigbridge.id.vn/terms"
description: "Public Terms route rendered from the current backend-supplied GigBridge Vietnam policy document."
---

# Terms of Service

The Terms route provides public access to GigBridge's current policy document through the shared Policy screen. It is linked from the Signup consent area so new users can review the governing information before creating an account.

---

## 1. Page Access & Purpose

- **Route**: `/terms`
- **Access**: Public.
- **Signup Link**: Opens in a separate tab from the registration policy-consent section.
- **Content Source**: The application requests the current GigBridge Vietnam policy Markdown from the backend.

---

## 2. Document Presentation

The page renders server-provided headings, lists, links, tables, quotes, and separators. External links open in a new browser tab, and wide policy tables remain scrollable on small screens.

Because `/terms`, `/privacy`, and `/policies` currently use the same Policy screen and endpoint, users should rely on the heading and content in the loaded document rather than assuming each route contains a separately hard-coded file.

---

## 3. Loading & Errors

- A loading status appears while the policy is requested.
- A successful response displays the Markdown article.
- An error response displays a message and a Retry button.
- Retrying reloads the server document; it does not submit signup or accept the policy on the user's behalf.

---

## 4. Acceptance During Signup

Opening or reading this route does not itself record acceptance. During email signup, the user must return to the registration form, select the policy-consent checkbox, complete email verification, and submit the account form.
