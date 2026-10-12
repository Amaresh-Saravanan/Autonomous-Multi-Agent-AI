"""`/ws/alerts` (Phase 22). Browsers can't set custom headers on a
WebSocket handshake, so the JWT travels as a query parameter — same
token issued by `/api/v1/auth/login`, just a different transport."""

import asyncio
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.errors import AuthenticationError
from app.infrastructure.database import SessionLocal
from app.infrastructure.websocket import get_connection_manager
from app.models.security import User
from app.security.jwt import decode_access_token

router = APIRouter(tags=["websocket"])

HEARTBEAT_TIMEOUT_S = 30


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_access_token(token)
    except AuthenticationError:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(payload["sub"]))
    finally:
        db.close()

    if user is None or not user.is_active:
        await websocket.close(code=4401)
        return

    manager = get_connection_manager()
    await manager.connect(websocket, user)
    try:
        while True:
            await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_TIMEOUT_S)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        manager.disconnect(websocket)
