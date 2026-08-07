# Week 1: Core FastAPI Setup & Security Configurations

This guide details the core framework configuration and bootstrapping tasks implemented in Week 1.

## 1. Project Initialization & Structure
The project is organized using a clean layer structure dividing endpoints, validation schemas, use-case services, database connections, and external clients.

Key files created:
*   `app/main.py`: Entry point configuring FastAPI, middleware (CORS), registering exception handlers, and routing API paths.
*   `app/core/config.py`: Loads environment configurations using Pydantic Settings from `.env`.
*   `app/core/exceptions.py`: Configures standard error response envelopes (`StandardResponse`).
*   `app/core/security.py`: API Key verification middleware.

## 2. Environment Variables Validation
We use Pydantic Settings to automatically cast, validate, and verify that configurations are loaded properly at startup, preventing runtime crashes.
Required parameters:
*   `HOST` / `PORT`
*   `AI_SERVER_API_KEY` (Incoming client validator token)
*   `OPENAI_API_KEY` / `GEMINI_API_KEY` / `CLAUDE_API_KEY` / `ELEVENLABS_API_KEY`

## 3. Client Verification Middleware
Incoming HTTP REST requests must contain the API key token inside the request header:
```http
X-API-Key: <your_key>
```
If missing or invalid, the server raises a custom `SecurityException` which resolves to a standardized JSON response:
```json
{
  "success": false,
  "message": "Invalid API Key.",
  "data": null,
  "errors": []
}
```
