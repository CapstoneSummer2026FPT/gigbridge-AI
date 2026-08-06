---
title: "GigBridge AI Assistant"
source: "https://gigbridge.id.vn/ai-assistant"
description: "Knowledge-base assistant widget available throughout the GigBridge application."
---

# AI Assistant

**Entry route:** `/ai-assistant` opens the assistant on the current application shell.

**Access:** Available through the AI Assistant navigation action.

The AI Assistant is a floating conversational widget rather than a standalone content screen. Users can ask questions about GigBridge features and workflows, use suggested prompts, and continue a conversation with prior message history.

Questions are sent to the AI service through the backend using the `general-knowledge` collection. Answers are generated from ingested knowledge-base documents such as the files in this folder. The assistant should explain platform usage; it cannot perform wallet, contract, proposal, or account actions on the user's behalf.

If the AI service cannot answer, the widget displays an error/retry state rather than treating a guessed response as a completed platform action.
