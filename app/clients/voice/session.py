"""Redis-backed session manager for voice interviews.

Key schema (all keys prefixed by namespace):
  session:{session_id}                    → hash   {job_id, freelancer_id, mode, language, question_index}  TTL: REDIS_SESSION_TTL
  session:{session_id}:history            → list   [{role, content, language}, ...]  TTL: REDIS_HISTORY_TTL
  draft:{session_id}                      → string JSON {draft_id, question_index, transcript, language, stt_provider, confidence, created_at}  TTL: REDIS_DRAFT_TTL
  tts_cache:{session_id}:q_{N}           → bytes  audio data  TTL: REDIS_TTS_CACHE_TTL
  confirmed:{session_id}                  → string "1" (set after successful confirm, for conflict detection)
"""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import VoiceProviderException
from app.clients.voice.models import DraftData, InterviewSession

logger = logging.getLogger("ai_server.voice.session")

# ── Lua script for GETDEL fallback (Redis < 6.2) ─────────────────
_GETDEL_LUA = """
local val = redis.call('GET', KEYS[1])
if val then redis.call('DEL', KEYS[1]) end
return val
"""


class VoiceSessionManager:
    """Redis-backed session manager for voice interviews.

    Handles session lifecycle, draft storage with atomic consume,
    TTS caching, and conversation history persistence.
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._getdel_sha: Optional[str] = None

    # ── Public helpers ─────────────────────────────────────────

    def redis(self) -> aioredis.Redis:
        """Lazy-init and return the Redis connection."""
        if self._redis is None:
            if not settings.REDIS_URL:
                raise VoiceProviderException("REDIS_URL not configured")
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    # ── Session CRUD ───────────────────────────────────────────

    async def create_session(self, data: dict) -> InterviewSession:
        """Create a new interview session in Redis.

        Args:
            data: Must include job_id, freelancer_id, mode, language.
                  Optional: session_id (generated if not provided).

        Returns:
            InterviewSession populated from stored data.
        """
        r = self.redis()
        session_id = data.get("session_id", f"int_{uuid.uuid4().hex[:12]}")

        mapping = {
            "job_id": data["job_id"],
            "freelancer_id": data.get("freelancer_id", ""),
            "mode": data.get("mode", "voice"),
            "language": data.get("language", "vi"),
            "question_index": str(data.get("question_index", 1)),
        }

        key = f"session:{session_id}"
        await r.hset(key, mapping=mapping)
        await r.expire(key, settings.REDIS_SESSION_TTL)

        logger.info("Session created: %s (lang=%s, mode=%s)", session_id, mapping["language"], mapping["mode"])
        return InterviewSession(
            session_id=session_id,
            job_id=mapping["job_id"],
            freelancer_id=mapping["freelancer_id"],
            mode=mapping["mode"],
            language=mapping["language"],
            question_index=int(mapping["question_index"]),
        )

    async def load_or_expire(self, session_id: str) -> Optional[InterviewSession]:
        """Load a session if it exists and hasn't expired.

        Returns:
            InterviewSession if found, None if expired or missing.
        """
        r = self.redis()
        key = f"session:{session_id}"
        data = await r.hgetall(key)
        if not data:
            return None

        return InterviewSession(
            session_id=session_id,
            job_id=data.get("job_id", ""),
            freelancer_id=data.get("freelancer_id", ""),
            mode=data.get("mode", "text"),
            language=data.get("language", "vi"),
            question_index=int(data.get("question_index", 1)),
        )

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and all associated data."""
        r = self.redis()
        keys = [
            f"session:{session_id}",
            f"session:{session_id}:history",
            f"draft:{session_id}",
            f"confirmed:{session_id}",
        ]
        # Also delete any TTS cache keys for this session
        cursor = 0
        while True:
            cursor, tts_keys = await r.scan(
                cursor, match=f"tts_cache:{session_id}:q_*"
            )
            keys.extend(tts_keys)
            if cursor == 0:
                break
        if keys:
            await r.delete(*keys)
        logger.info("Deleted session data: %s (%d keys)", session_id, len(keys))

    # ── Draft Management (atomic via GETDEL) ───────────────────

    async def save_draft(self, session_id: str, draft: DraftData) -> None:
        """Save a transcription draft as JSON in Redis with TTL."""
        r = self.redis()
        key = f"draft:{session_id}"
        await r.set(key, json.dumps(self._draft_to_dict(draft)))
        await r.expire(key, settings.REDIS_DRAFT_TTL)
        logger.debug("Draft saved: %s (q=%d)", session_id, draft.question_index)

    async def consume_draft(self, session_id: str) -> Optional[DraftData]:
        """Atomically consume a draft via GETDEL.

        Returns:
            DraftData if a draft existed, None if expired or already consumed.

        This is the atomic guarantee — GETDEL returns the value AND deletes
        it in one operation, preventing double-confirm races.
        """
        r = self.redis()
        key = f"draft:{session_id}"
        raw = await self._atomic_getdel(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
            return DraftData(
                draft_id=data["draft_id"],
                question_index=data["question_index"],
                transcript=data["transcript"],
                language=data.get("language", "vi"),
                stt_provider=data.get("stt_provider", ""),
                confidence=float(data.get("confidence", 0.0)),
                created_at=data.get("created_at", ""),
                confirmed=data.get("confirmed", False),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to parse draft JSON for %s: %s", session_id, exc)
            return None

    async def mark_confirmed(self, session_id: str) -> None:
        """Mark a session as having a confirmed answer (for conflict detection)."""
        r = self.redis()
        key = f"confirmed:{session_id}"
        await r.set(key, "1")
        await r.expire(key, settings.REDIS_SESSION_TTL)

    async def is_confirmed(self, session_id: str) -> bool:
        """Check if this session already has a confirmed answer."""
        r = self.redis()
        return await r.exists(f"confirmed:{session_id}") > 0

    # ── TTS Cache ──────────────────────────────────────────────

    async def cache_tts(self, session_id: str, question_index: int, audio_bytes: bytes) -> None:
        """Cache TTS audio for a given question.

        Stores as base64 to avoid decode_responses=True binary corruption.
        """
        r = self.redis()
        key = f"tts_cache:{session_id}:q_{question_index}"
        encoded = base64.b64encode(audio_bytes).decode("ascii")
        await r.set(key, encoded)
        await r.expire(key, settings.REDIS_TTS_CACHE_TTL)
        logger.debug("TTS cached: %s q=%d (%d bytes raw)", session_id, question_index, len(audio_bytes))

    async def get_cached_tts(self, session_id: str, question_index: int) -> Optional[bytes]:
        """Retrieve cached TTS audio, or None if not cached/expired.

        Decodes from base64 storage.
        """
        r = self.redis()
        key = f"tts_cache:{session_id}:q_{question_index}"
        raw = await r.get(key)
        if raw is None:
            return None
        try:
            return base64.b64decode(raw)
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to decode cached TTS for %s q=%d: %s", session_id, question_index, exc)
            return None

    # ── Pointer Advancement ────────────────────────────────────

    async def advance_pointer(self, session_id: str) -> int:
        """Atomically increment the question_index for a session.

        Returns the NEW question_index after increment.
        """
        r = self.redis()
        key = f"session:{session_id}"
        new_index = await r.hincrby(key, "question_index", 1)
        # Refresh TTL on access
        await r.expire(key, settings.REDIS_SESSION_TTL)
        logger.debug("Pointer advanced: %s → q=%d", session_id, new_index)
        return new_index

    # ── Conversation History ───────────────────────────────────

    async def add_history(self, session_id: str, role: str, content: str, language: str) -> None:
        """Append a conversation turn to the Redis history list."""
        r = self.redis()
        key = f"session:{session_id}:history"
        entry = json.dumps({"role": role, "content": content, "language": language})
        await r.rpush(key, entry)
        await r.expire(key, settings.REDIS_HISTORY_TTL)
        logger.debug("History appended: %s role=%s", session_id, role)

    async def get_history(self, session_id: str) -> list[dict]:
        """Retrieve full conversation history as a list of dicts."""
        r = self.redis()
        key = f"session:{session_id}:history"
        entries = await r.lrange(key, 0, -1)
        result = []
        for entry in entries:
            try:
                result.append(json.loads(entry))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed history entry for %s", session_id)
                continue
        return result

    # ── Private helpers ────────────────────────────────────────

    async def _atomic_getdel(self, key: str) -> Optional[str]:
        """Perform GETDEL, with Lua fallback for Redis < 6.2."""
        r = self.redis()
        try:
            # Redis 6.2+ — native GETDEL
            return await r.getdel(key)
        except Exception:
            # Fallback: try Lua script
            try:
                if self._getdel_sha is None:
                    self._getdel_sha = await r.script_load(_GETDEL_LUA)
                return await r.evalsha(self._getdel_sha, 1, key)
            except Exception:
                # Final fallback: GET + DEL (not atomic, but works)
                val = await r.get(key)
                if val is not None:
                    await r.delete(key)
                return val

    @staticmethod
    def _draft_to_dict(draft: DraftData) -> dict:
        return {
            "draft_id": draft.draft_id,
            "question_index": draft.question_index,
            "transcript": draft.transcript,
            "language": draft.language,
            "stt_provider": draft.stt_provider,
            "confidence": draft.confidence,
            "created_at": draft.created_at,
            "confirmed": draft.confirmed,
        }
