import asyncio
import logging
import threading
import time

from app.config import settings
from app.models.schemas import ChatMessage

logger = logging.getLogger(__name__)


class SessionManager:
    """In-memory session storage with automatic TTL-based cleanup."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._last_activity: dict[str, float] = {}
        self._lock = threading.Lock()
        self._cleanup_task: asyncio.Task | None = None

    def get_history(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        with self._lock:
            if session_id not in self._sessions:
                if len(self._sessions) >= settings.session_max_count:
                    self._evict_oldest()
                self._sessions[session_id] = []
            history = self._sessions[session_id]
            history.append(message)
            self._last_activity[session_id] = time.monotonic()
            # Trim to max history (keep last N messages)
            max_len = settings.session_max_history
            if len(history) > max_len:
                self._sessions[session_id] = history[-max_len:]

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._last_activity.pop(session_id, None)

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def get_message_count(self, session_id: str) -> int:
        with self._lock:
            return len(self._sessions.get(session_id, []))

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def _evict_oldest(self) -> None:
        """Remove the least recently active session. Must be called under lock."""
        if not self._last_activity:
            return
        oldest = min(self._last_activity, key=self._last_activity.get)
        self._sessions.pop(oldest, None)
        self._last_activity.pop(oldest, None)
        logger.info("Evicted inactive session %s (max count reached)", oldest)

    def _cleanup_expired(self) -> None:
        """Remove sessions that exceeded TTL."""
        ttl_seconds = settings.session_ttl_minutes * 60
        now = time.monotonic()
        with self._lock:
            expired = [
                sid for sid, ts in self._last_activity.items()
                if now - ts > ttl_seconds
            ]
            for sid in expired:
                self._sessions.pop(sid, None)
                self._last_activity.pop(sid, None)
            if expired:
                logger.info("Cleaned up %d expired sessions", len(expired))

    async def _periodic_cleanup(self) -> None:
        """Background task that periodically cleans up expired sessions."""
        interval = max(60, settings.session_ttl_minutes * 60 // 2)
        while True:
            await asyncio.sleep(interval)
            self._cleanup_expired()

    def start_cleanup_task(self) -> None:
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    def stop_cleanup_task(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None


session_manager = SessionManager()
