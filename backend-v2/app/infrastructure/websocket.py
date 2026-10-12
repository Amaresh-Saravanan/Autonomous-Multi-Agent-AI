"""WebSocket connection registry + Redis pub/sub bridge (Phase 22).
Replaces V1's open socket broadcasting every incident to every client:
connections are grouped by agency, and a message published on
`alerts:{agency_id}` only reaches sockets authenticated for that agency
(ADMIN connections see every channel)."""

import asyncio
import json
import logging

from fastapi import WebSocket

from app.infrastructure.redis import RedisLike
from app.models.security import RoleEnum, User

logger = logging.getLogger("app.websocket")


class ConnectionManager:
    def __init__(self):
        self._connections: dict[WebSocket, User] = {}

    async def connect(self, websocket: WebSocket, user: User) -> None:
        await websocket.accept()
        self._connections[websocket] = user

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, target_agency_id: str | None, payload: dict) -> None:
        """`target_agency_id` is the agency the alert was published for, or
        None/"unassigned", or "global" (situation-level alerts every authenticated
        socket receives). ADMIN sockets receive everything; everyone else
        only receives messages for their own agency."""
        stale = []
        for websocket, user in self._connections.items():
            if (
                target_agency_id != "global"
                and user.role != RoleEnum.ADMIN
                and str(user.agency_id) != target_agency_id
            ):
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _manager


async def run_pubsub_bridge(redis_client: RedisLike, manager: ConnectionManager, stop_event: asyncio.Event) -> None:
    """Background task (Phase 22: Redis Pub/Sub for multi-worker event
    distribution): forwards every `alerts:*` publish to matching sockets.
    Uses `asyncio.to_thread` so the blocking sync-redis call never stalls
    the event loop (Phase 2's sync-DB-on-async-WebSocket constraint applies
    equally to sync Redis here)."""
    pubsub = redis_client.pubsub()
    pubsub.psubscribe("alerts:*")
    try:
        while not stop_event.is_set():
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if message is None or message.get("type") != "pmessage":
                continue
            channel = message["channel"]
            channel = channel.decode() if isinstance(channel, bytes) else channel
            agency_id = channel.split(":", 1)[1]
            data = message["data"]
            data = data.decode() if isinstance(data, bytes) else data
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Dropping malformed pubsub message on %s", channel)
                continue
            await manager.broadcast(agency_id, payload)
    finally:
        pubsub.close()
