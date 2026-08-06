---
title: "GigBridge Notifications"
source: "https://gigbridge.id.vn/notifications"
description: "Notification inbox for jobs, proposals, contracts, messages, milestones, payments, reviews, disputes, AI suggestions, and schedules."
---

# Notifications

The Notifications page is the signed-in user's activity inbox. It distinguishes read and unread items, periodically refreshes the list, and can open the platform destination attached to a notification.

---

## 1. Page Access & Counters

- **Route**: `/notifications`
- **Access**: Authenticated users.
- **Unread Summary**: Shows the current unread count or an All Caught Up state.
- **Page Size**: Loads a notification page of up to 20 items through the current hook configuration.
- **Polling**: Checks for updated notification data approximately every 45 seconds while the page is active.

---

## 2. Filters & Read State

- **All Tab**: Shows every loaded notification and its total count.
- **Unread Tab**: Filters the loaded list to items not yet marked as read.
- **Mark All as Read**: Available only when the unread count is greater than zero.
- **Unread Indicator**: A visual dot and different card styling distinguish unread activity.

Changing tabs does not delete notifications; it only changes which loaded items are visible.

---

## 3. Notification Categories

The interface provides distinct icons for:

- Jobs and proposals.
- Contracts and messages.
- Milestones and payments.
- Reviews and disputes.
- AI suggestions and system notices.
- Scheduled events.

Each item can contain a title, body, relative creation time, and optional destination URL.

---

## 4. Opening a Notification

Selecting an item first requests that it be marked as read. If the notification has an `actionUrl`, the application then navigates to that destination.

Scheduled notifications may additionally show the schedule title, actor name, and event time formatted in the **Asia/Ho_Chi_Minh** time zone and labeled ICT.

---

## 5. Loading & Empty States

- While data is loading, the page shows that it is checking the inbox.
- If the selected filter contains no items, it displays No Notifications and explains that new activity will appear there.
- A notification describes activity but does not itself guarantee that a proposal, contract, milestone, payment, or review action succeeded; open the linked page to confirm the underlying state.
