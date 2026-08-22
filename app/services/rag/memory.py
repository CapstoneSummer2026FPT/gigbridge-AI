"""
PURPOSE: Multi-tiered conversation memory manager (short-term conversation history, user preferences, and domain contexts).
IMPORTANCE: High — Manages conversation memory logs and candidate preferences.
READING FLOW: app/services/rag/memory.py -> app/services/rag/query_engine.py
"""

from typing import Any, Dict, List, Optional


class MemoryManager:
    """Manages multi-tiered memory structures for chat sessions, user preferences, and domain contexts."""

    def __init__(self):
        """Initialize in-memory stores for conversations, user preferences, and domain memories."""
        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        self._domain_memories: Dict[str, Dict[str, Any]] = {
            "job_posts": {},
            "interviews": {},
            "talent_matching": {}
        }

    # === SHORT-TERM CONVERSATION MEMORY ===

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieve the last N messages for an active chat session."""
        history = self._conversations.get(session_id, [])
        return history[-limit:]

    async def add_to_conversation_history(self, session_id: str, role: str, content: str) -> None:
        """Append a message turn to active chat history."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append({"role": role, "content": content})

    async def clear_conversation_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self._conversations:
            self._conversations[session_id] = []

    # === USER PREFERENCE MEMORY ===

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Load candidate preferences (target budget, remote preference, skill keywords)."""
        return self._user_preferences.get(user_id, {
            "experience_level": "intermediate",
            "preferred_locations": ["Remote"],
            "target_hourly_rate": None,
            "tone_style": "professional"
        })

    async def save_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update a user preference metric."""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][key] = value

    # === DOMAIN MEMORY (Jobs, Interviews, Matching) ===

    async def save_domain_context(self, domain: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Persist domain context logs (e.g., parsed job posts, interview answers, matching scores)."""
        if domain in self._domain_memories:
            self._domain_memories[domain][entity_id] = data

    async def get_domain_context(self, domain: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Fetch historical context logs for specific domain entities."""
        if domain in self._domain_memories:
            return self._domain_memories[domain].get(entity_id)
        return None


_memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Dependency injection helper returning singleton instance of MemoryManager."""
    return _memory_manager
