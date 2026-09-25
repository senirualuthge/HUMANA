"""
humana/app/services/session_manager.py
In-memory WebSocket session registry.
Tracks active connections per business for the Live Monitor.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional, Set

from fastapi import WebSocket

from app.core.logging import get_logger

log = get_logger(__name__)


class Session:
    def __init__(self, ws: WebSocket, business_id: str, session_id: str):
        self.ws = ws
        self.business_id = business_id
        self.session_id = session_id
        self.connected_at = datetime.now(timezone.utc)
        self.message_count = 0
        self.last_ping: Optional[datetime] = None

    async def send(self, data: dict) -> bool:
        try:
            await self.ws.send_json(data)
            return True
        except Exception as exc:
            log.warning("ws_send_failed", session_id=self.session_id, error=str(exc))
            return False


class SessionManager:
    """
    Thread-safe (asyncio) session registry.

    Structure:
        _sessions: {session_id -> Session}
        _by_business: {business_id -> set[session_id]}
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._by_business: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, business_id: str, session_id: str) -> Session:
        await ws.accept()
        session = Session(ws, business_id, session_id)
        async with self._lock:
            self._sessions[session_id] = session
            self._by_business[business_id].add(session_id)
        log.info("ws_connected", business_id=business_id, session_id=session_id,
                 total=len(self._sessions))
        return session

    async def disconnect(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                self._by_business[session.business_id].discard(session_id)
                if not self._by_business[session.business_id]:
                    del self._by_business[session.business_id]
        log.info("ws_disconnected", session_id=session_id,
                 total=len(self._sessions))

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def sessions_for(self, business_id: str) -> list[Session]:
        ids = self._by_business.get(business_id, set())
        return [self._sessions[sid] for sid in ids if sid in self._sessions]

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    @property
    def active_by_business(self) -> Dict[str, int]:
        return {bid: len(sids) for bid, sids in self._by_business.items()}

    async def broadcast(self, business_id: str, data: dict) -> int:
        """Send a message to ALL sessions of a business. Returns sent count."""
        sent = 0
        for session in self.sessions_for(business_id):
            if await session.send(data):
                sent += 1
        return sent


# Global singleton
session_manager = SessionManager()
