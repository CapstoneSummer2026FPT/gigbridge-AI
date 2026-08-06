---
title: "GigBridge AI Assistant"
source: "https://gigbridge.id.vn/ai-assistant"
description: "Floating knowledge-base assistant with contextual prompts, persistent history, speech input, read-aloud answers, and explicit service states."
---

# AI Assistant

The AI Assistant is a floating widget rendered throughout the application rather than a standalone full-page screen. Navigating to `/ai-assistant` redirects to the homepage with state that opens the widget automatically.

---

## 1. Access & Conversation Context

- **Navigation Route**: `/ai-assistant`
- **Presentation**: Floating action button and expandable chat panel.
- **Open Triggers**: The navigation redirect, widget button, or global toggle event.
- **Conversation Storage**: Messages persist in browser local storage under the widget session key and survive tab reloads until cleared.
- **Unread Count**: Responses received while the panel is closed increase the widget badge and clear when it is opened.

---

## 2. Contextual Suggestions

Suggested prompts change with the current route:

- Browse/Saved/Job Details: proposal writing, Client questions, and bidding guidance.
- Job Posting: job descriptions, screening questions, and milestone planning.
- Proposals: pitch review, price justification, and follow-up messages.
- Contracts/Projects/Workspace: progress reports, review requests, and project risks.
- Other pages: general project, hiring, and interview assistance.

Selecting a suggestion sends it as a normal user question.

---

## 3. Knowledge Retrieval

Questions are sent to `ai-assistant/query` with prior conversation history, the `general-knowledge` collection, and precision style. The widget appends an AI disclaimer to displayed answers while excluding prior disclaimers from the next history payload.

- Maximum user message length is **5,000 characters**.
- A five-second client timer changes the display to a slow-response/timeout state, although the underlying request may still resolve.
- Service responses are presented as guidance, not proof that a platform transaction occurred.

---

## 4. Voice, Audio & Message Tools

- **Speech Input**: Uses browser SpeechRecognition/WebKit SpeechRecognition with Vietnamese recognition when supported; recognized text is added to the input.
- **Read Aloud**: Uses browser speech synthesis, preferring a Vietnamese voice and otherwise using English.
- **Sound Effects**: Optional local send, receive, and opening sounds.
- **Copy**: Copies an answer to the clipboard.
- **Clear**: Removes stored conversation history and resets service/error state.
- **Minimize/Close**: Hides the panel without necessarily clearing its history.

Unsupported speech recognition produces a browser-support message rather than disabling text chat.

---

## 5. Service States & Limitations

- **Ready**: Accepts a new question.
- **Thinking**: Prevents duplicate sends while a request is active.
- **Timeout**: Indicates the response is taking longer than expected.
- **Unavailable**: Shows a backend or network error and allows a later retry.

The assistant can explain features and help draft text. It cannot submit proposals, alter job posts, send messages, sign contracts, approve milestones, move escrow, purchase Premium, or change account settings on the user's behalf.
