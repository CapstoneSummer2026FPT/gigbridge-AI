---
title: "GigBridge Google Meet OAuth Integration"
source: "https://gigbridge.id.vn/integrations/google-meet/callback"
description: "OAuth callback page handling Google Calendar and Google Meet (ggmeet, gmeet) OAuth authorization for interview, negotiation room, and project meeting scheduling."
keywords: "ggmeet, gmeet, google meet, negotiation, scheduling, video call, google workspace, oauth"
---

# Google Meet Integration (ggmeet, gmeet)

The Google Meet OAuth Integration callback page handles the OAuth 2.0 authorization code redirect flow, allowing Clients and Freelancers to connect their Google Workspace accounts for automated video call scheduling in Messages, Negotiation rooms, AI Interviews, and Project Workspaces.

---

## 1. Page Access & Redirect Flow

- **Route**: `/integrations/google-meet/callback`
- **Access**: Public endpoint triggered by Google OAuth 2.0 authorization server redirects.
- **URL Parameters**: Accepts `code` (authorization grant), `state` (CSRF security token and user context), and `error` (if user cancelled authorization).

---

## 2. Processing & Account Linking

1. **Token Exchange**: The frontend receives the OAuth authorization code and sends it to the backend (`/api/Integrations/google-meet/callback`).
2. **Access Token Generation**: The backend exchanges the code for access and refresh tokens via Google OAuth API.
3. **Calendar Scope Grant**: Authorizes `https://www.googleapis.com/auth/calendar.events` to schedule Google Meet video links automatically.
4. **User Profile Update**: Marks Google Meet integration as `Connected` in user settings.

---

## 3. Success & Failure UI Feedback

- **Success State**: Displays a confirmation message ("Google Workspace Successfully Connected!") and redirects user back to `/settings` or the calling AI Interview screen after 3 seconds.
- **Failure State**: Displays error message (e.g., "Authorization Denied by User" or "OAuth State Mismatch") with a button to retry connecting from `/settings`.
