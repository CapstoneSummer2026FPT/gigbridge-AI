# Week 4: Memory Architecture & Prompt Compiler

This guide covers the memory management structures and LLM Router routing configurations built in Week 4.

## 1. Multi-tiered Memory Managers
We implement a `MemoryManager` (`app/services/memory.py`) dividing memory into three functional categories:
1.  **Short-Term Memory (`ConversationMemory`)**: Keeps track of message history within an active interview session ID, ensuring the model remembers previous answers.
2.  **User Preference Memory (`UserPreferenceMemory`)**: Tracks candidate expectations, target rates, and work configurations to tailor outputs.
3.  **Domain Memory (`DomainMemory`)**: Holds metadata on jobs, interviews, and matching outcomes.

## 2. Prompt Template Compiler
System prompts are separated into text templates under `app/prompts/templates/`. The `PromptManager` class:
*   Initializes a **Jinja2** filesystem environment.
*   Loads templates dynamically and compiles them with runtime variables.
*   Keeps fallback strings in python in case templates fail to load.

## 3. LLM Gateway & Fallback Router
The `LLMGateway` (`app/clients/llm/gateway.py`) orchestrates completion requests across model providers, preventing system outages:
*   **Routing Priority**: Try `OpenAI` (Primary) -> `Gemini` (Fallback 1) -> `Claude` (Fallback 2) -> `Local Model` (Ollama - Fallback 3).
*   **Outage Failover Loop**: If the primary client throws an HTTP error or timeout, the gateway catches the exception, logs it, and immediately forwards the query to the next available fallback provider, ensuring 100% uptime.
