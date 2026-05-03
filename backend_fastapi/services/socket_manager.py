"""WebSocket Connection Manager – robust, multi-tab aware.

Architecture:
  • connections: dict[int, list[WebSocket]]
      Each user can have multiple connections (different tabs/devices).
  • All messages are persisted to DB *before* WebSocket delivery.
  • If the recipient is offline, the message stays in DB and is
    delivered when they connect and request history.

Thread-safety: FastAPI runs each WebSocket in its own asyncio task,
so we use a standard asyncio.Lock for concurrent access.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per user_id.

    Usage:
        manager = ConnectionManager()

        @app.websocket("/ws/chat")
        async def chat(websocket: WebSocket, user_id: int = Depends(...)):
            await manager.connect(user_id, websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.handle_message(user_id, data)
            finally:
                manager.disconnect(user_id, websocket)
    """

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    # ── Connect ────────────────────────────────────────────────────────
    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Accept a WebSocket and register it for the user.

        If the user already has connections, this one is appended
        (multi-tab support).
        """
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(websocket)
        logger.info(
            "WS connect: user=%d | total connections for user: %d",
            user_id,
            len(self._connections[user_id]),
        )

    # ── Disconnect ─────────────────────────────────────────────────────
    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Remove a specific WebSocket from the user's connection list."""
        async with self._lock:
            if user_id in self._connections:
                try:
                    self._connections[user_id].remove(websocket)
                except ValueError:
                    pass
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info("WS disconnect: user=%d", user_id)

    # ── Send to a specific user (all their open connections) ───────────
    async def send_personal_message(
        self,
        user_id: int,
        data: dict[str, Any],
    ) -> int:
        """Send a JSON message to all connections of a user.

        Returns the number of connections the message was sent to.
        """
        payload = json.dumps(data, default=str)
        sent_count = 0
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for ws in connections[:]:  # iterate over a copy
                try:
                    await ws.send_text(payload)
                    sent_count += 1
                except Exception:
                    # Connection might have died; remove it
                    try:
                        connections.remove(ws)
                    except ValueError:
                        pass
        return sent_count

    # ── Broadcast to all connected users (admin use) ───────────────────
    async def broadcast(self, data: dict[str, Any]) -> int:
        """Send a message to every connected user. Returns count."""
        payload = json.dumps(data, default=str)
        sent_count = 0
        async with self._lock:
            for user_id, conns in list(self._connections.items()):
                for ws in conns[:]:
                    try:
                        await ws.send_text(payload)
                        sent_count += 1
                    except Exception:
                        try:
                            conns.remove(ws)
                        except ValueError:
                            pass
                if not conns:
                    del self._connections[user_id]
        return sent_count

    # ── Check online status ────────────────────────────────────────────
    def is_online(self, user_id: int) -> bool:
        """Return True if the user has at least one active connection."""
        return user_id in self._connections and bool(self._connections[user_id])

    async def get_online_users(self) -> list[int]:
        """Return a list of user IDs that are currently connected."""
        async with self._lock:
            return list(self._connections.keys())

    # ── Disconnect all connections for a user ──────────────────────────
    async def force_disconnect(self, user_id: int) -> None:
        """Forcefully close all WebSockets for a user (e.g. admin ban)."""
        async with self._lock:
            conns = self._connections.pop(user_id, [])
        for ws in conns:
            try:
                await ws.close(code=1000, reason="Forced disconnect")
            except Exception:
                pass


# ── Singleton – imported by routes ─────────────────────────────────────
manager = ConnectionManager()
