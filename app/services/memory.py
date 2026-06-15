from typing import List, Dict, Any, Optional

class MemoryManager:
    """Manages multi-tiered memory structures (Short-term conversation, User Preferences, and Domain Contexts)"""
    
    def __init__(self):
        # In-memory store (simulating Redis/persistent database caches)
        self._conversations: Dict[str, List[Dict[str, str]]] = {}
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        self._domain_memories: Dict[str, Dict[str, Any]] = {
            "job_posts": {},
            "interviews": {},
            "talent_matching": {}
        }

    # === SHORT-TERM CONVERSATION MEMORY ===
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieves the last N messages for an active chat session.
        """
        history = self._conversations.get(session_id, [])
        return history[-limit:]

    async def add_to_conversation_history(self, session_id: str, role: str, content: str) -> None:
        """
        Appends a message to chat history.
        """
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append({"role": role, "content": content})

    async def clear_conversation_history(self, session_id: str) -> None:
        """
        Clears chat logs.
        """
        if session_id in self._conversations:
            self._conversations[session_id] = []

    # === USER PREFERENCE MEMORY ===
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Loads candidate preferences (target budget, remote preference, skill keywords).
        """
        return self._user_preferences.get(user_id, {
            "experience_level": "intermediate",
            "preferred_locations": ["Remote"],
            "target_hourly_rate": None,
            "tone_style": "professional"
        })

    async def save_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """
        Updates a user preference metric.
        """
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][key] = value

    # === DOMAIN MEMORY (Jobs, Interviews, Matching) ===
    async def save_domain_context(self, domain: str, entity_id: str, data: Dict[str, Any]) -> None:
        """
        Persists domain context logs (e.g., parsed job posts, interview answers, matching scores).
        
        Args:
            domain: 'job_posts', 'interviews', or 'talent_matching'
            entity_id: The primary identifier of the entity
            data: Key-value values to store
        """
        if domain in self._domain_memories:
            self._domain_memories[domain][entity_id] = data

    async def get_domain_context(self, domain: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches historical context logs for specific domain entities.
        """
        if domain in self._domain_memories:
            return self._domain_memories[domain].get(entity_id)
        return None

# Dependency helper
_memory_manager = MemoryManager()

def get_memory_manager() -> MemoryManager:
    return _memory_manager
