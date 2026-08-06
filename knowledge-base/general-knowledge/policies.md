---
title: "GigBridge Policies"
source: "https://gigbridge.id.vn/policies"
description: "Public policy viewer that loads and renders the current GigBridge Vietnam policy document."
---

# Policies

The Policies page displays the current GigBridge Vietnam policy content supplied by the backend. The same policy screen component is used for the policy-related public routes, so the server-delivered document is the controlling content shown to users.

---

## 1. Page Access & Source

- **Route**: `/policies`
- **Access**: Public through the guest layout.
- **Content Source**: Loaded from the GigBridge Vietnam policy endpoint at page entry.
- **Rendering**: Markdown is rendered with GitHub-Flavored Markdown support.

The knowledge-base summary does not replace the policy text returned by the platform.

---

## 2. Supported Policy Formatting

The viewer supports headings, paragraphs, ordered and unordered lists, blockquotes, tables, horizontal separators, and links. Wide tables can scroll horizontally on smaller screens.

- **Internal Links**: Open within the normal browser context.
- **External Links**: Open in a new tab with safe link attributes.
- **Responsive Layout**: Uses the public guest layout and a centered article container.

---

## 3. Loading & Retry

1. The page begins with a loading status while requesting the policy.
2. On success, the returned Markdown string is rendered as the policy article.
3. On failure, the page shows the returned or translated error message.
4. The **Retry** button repeats the policy request.

A failed load does not mean the policy has been removed; it may reflect a temporary service or connectivity error.

---

## 4. Using the Policy

Users should read the current displayed document before registration, contracting, payment, reporting, or dispute activity. For account-specific questions, compare the policy with the exact contract and transaction state shown inside the authenticated platform.
