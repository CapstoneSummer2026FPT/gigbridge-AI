---
title: "GigBridge Browse Jobs"
source: "https://gigbridge.id.vn/jobs/browse"
description: "Detailed guide to searching, filtering, sorting, saving, and opening GigBridge project opportunities."
---

# Browse Jobs

Browse Jobs is the searchable catalog of project requests available to signed-in users. It combines backend search results with category, skill, budget, work-type, date, sorting, pagination, saved-job state, and sponsored content.

---

## 1. Page Access & Search

- **Route**: `/jobs/browse`
- **Access**: Authenticated users; saving is restricted to Freelancer accounts.
- **Keyword Search**: Searches the public-job service and stores the committed term in the `q` URL parameter.
- **Search Safety**: Removes unsafe punctuation and limits search text to 120 characters.
- **Result Tracking**: A search-event identifier may be carried across pages and recorded when a job is opened.

Pressing Enter or using the search action commits the current keyword and returns pagination to the first page.

---

## 2. Filters & Sorting

- **Category**: Choose All or a category loaded from available results; the selected category can be represented by `cat` in the URL.
- **Skills**: Enter skill keywords such as React or SQL.
- **Minimum & Maximum Budget**: Numeric GigCoin boundaries; minimum greater than maximum is rejected as an invalid range.
- **Work Type**: Filter by the available work-location/type options.
- **Date Posted**: Restrict results to a recent posting window or Any Time.
- **Sort**: Toggle between relevance and newest/date-posted ordering.

Category pills provide a faster alternative to the expanded filter panel. Changing a filter resets the page number.

---

## 3. Job Cards

Cards can show the project title, category, description excerpt, skills, GigCoin budget range, proposal count, posting date, remote/on-site context, AI or promotional indicators, and other data returned by search.

Selecting a card records the open event when possible and navigates to `/jobs/:id`. Sponsored cards and promotion panels are visually separate from ordinary search ranking.

---

## 4. Saving Jobs

1. A signed-in Freelancer selects the bookmark control on a job card.
2. GigBridge calls the save or unsave service and temporarily disables duplicate clicks for that job.
3. Success updates the local bookmark state and shows confirmation.
4. Failure restores the prior state and displays an error.

Clients cannot use the save-job control. Saving does not submit a proposal, reserve the job, or preserve eligibility if the job later closes.

---

## 5. Pagination, Sidebar & Empty States

- Pagination updates the `page` URL parameter and requests the corresponding backend result page.
- The sidebar can show sponsored opportunities, Freelancer promotion status, or top Freelancer information.
- Loading and request failures are distinct from a valid zero-result search.
- If no jobs match, broaden the keywords, clear restrictive filters, or correct the budget range.
