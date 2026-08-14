---
title: "GigBridge Admin System Tracking & Audit Logs"
source: "https://gigbridge.id.vn/admin/system-tracking"
description: "Administrator technical dashboard for monitoring real-time API performance, error logs, audit trail events, and microservice status."
---

# Admin System Tracking & Audit Logs

The Admin System Tracking & Audit Logs page provides technical administrators with diagnostic tools to inspect API traffic, exception traces, audit logs, background task execution, and third-party AI service health.

---

## 1. Page Access & Navigation

- **Routes**: `/admin/system-tracking`, `/admin/audit-logs` (redirects to `/admin/system-tracking`).
- **Access**: Restricted to `Admin` role.

---

## 2. Real-time Monitoring & Diagnostic Widgets

- **API Request Throughput**: Requests per minute across backend endpoints (`Gigbridge_ProjectCapstone` and `gigbridge-AI`).
- **Error Rate Tracker**: Live count of HTTP 4xx and 5xx responses with stack trace expandable previews.
- **Microservice Status Indicators**:
  - **Backend API (.NET Core)**: Health status and database connection latency.
  - **AI Microservice (FastAPI)**: RAG vector database status (ChromaDB), LiteLLM gateway status, Gladia STT, and ElevenLabs TTS connection state.

---

## 3. Audit Trail Logs

Log table recording administrative and system actions:
- **Timestamp**: High-precision ISO timestamp.
- **Actor**: System, User, or Admin ID.
- **Action / Event**: User Suspension, Escrow Release, Role Elevation, Contract Take-down, or Setting Modification.
- **IP Address & Client User Agent**: Geo-location and security audit context.
- **Log Payload**: Raw JSON viewer showing before-and-after state changes.
