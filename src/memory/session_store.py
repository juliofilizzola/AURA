"""In-memory session store com TTL e limite de mensagens.

Cada sessão é identificada por um session_id (string) e mantém uma lista de
mensagens no formato {"role": ..., "content": ...}. Sessões expiram após
inatividade configur ável (TTL) e têm limite de mensagens (FIFO).

Sem persistência — os dados são perdidos ao reiniciar o processo.
"""

import threading
import time
from collections import deque
from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


class _Session:
    def __init__(self, max_messages: int):
        self._messages: deque[Message] = deque(maxlen=max_messages)
        self.last_access: float = time.monotonic()

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})
        self.last_access = time.monotonic()

    def messages(self) -> list[Message]:
        self.last_access = time.monotonic()
        return list(self._messages)


class SessionStore:
    """Thread-safe in-memory store for conversation sessions."""

    def __init__(self, ttl_minutes: float = 30.0, max_messages: int = 50):
        self._ttl_seconds = ttl_minutes * 60
        self._max_messages = max_messages
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()

    def _evict_expired(self) -> None:
        """Remove sessões expiradas (chamado com o lock já adquirido)."""
        now = time.monotonic()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_access > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]

    def get_history(self, session_id: str) -> list[Message]:
        """Retorna o histórico da sessão ou lista vazia se não existir."""
        with self._lock:
            self._evict_expired()
            session = self._sessions.get(session_id)
            return session.messages() if session else []

    def append(self, session_id: str, role: str, content: str) -> None:
        """Adiciona uma mensagem à sessão, criando-a se não existir."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = _Session(self._max_messages)
            self._sessions[session_id].add(role, content)

    def clear(self, session_id: str) -> None:
        """Remove a sessão completamente."""
        with self._lock:
            self._sessions.pop(session_id, None)
