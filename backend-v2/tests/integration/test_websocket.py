import asyncio

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.websocket import ConnectionManager
from app.main import app
from app.models.security import Agency, RoleEnum, User
from app.security.auth import hash_password
from app.security.jwt import create_access_token


def _make_user(db, role=RoleEnum.VIEWER):
    agency = Agency(name="WS Agency", code="WSA")
    db.add(agency)
    db.commit()
    user = User(email=f"{role.value.lower()}@ws.test", hashed_password=hash_password("x"), role=role, agency_id=agency.id)
    db.add(user)
    db.commit()
    return user, agency


def test_ws_rejects_invalid_token(db):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/alerts?token=not-a-real-token"):
            pass


def test_ws_accepts_valid_token_and_registers_connection(db):
    user, _ = _make_user(db)
    token = create_access_token(subject=str(user.id), role=user.role.value, agency_id=str(user.agency_id))

    client = TestClient(app)
    with client.websocket_connect(f"/ws/alerts?token={token}"):
        pass  # connection accepted without raising


def test_connection_manager_filters_broadcast_by_agency():
    """Agency-scoped fan-out (Phase 22): a message for agency A must not be
    delivered to a VIEWER/OPERATOR socket registered under agency B."""

    class _FakeSocket:
        def __init__(self):
            self.received = []

        async def accept(self):
            pass

        async def send_json(self, payload):
            self.received.append(payload)

    class _FakeUser:
        def __init__(self, role, agency_id):
            self.role = role
            self.agency_id = agency_id

    async def scenario():
        manager = ConnectionManager()
        socket_a, socket_b = _FakeSocket(), _FakeSocket()
        await manager.connect(socket_a, _FakeUser(RoleEnum.VIEWER, "agency-a"))
        await manager.connect(socket_b, _FakeUser(RoleEnum.VIEWER, "agency-b"))

        await manager.broadcast("agency-a", {"message": "for agency A only"})

        assert socket_a.received == [{"message": "for agency A only"}]
        assert socket_b.received == []

    asyncio.run(scenario())
