"""RBAC: JWT auth + in-memory user store (tracker 3.4, SEC-1).

Roles: admin, operator, viewer (YAGNI — no finer grading than the dashboard
currently needs; admin implicitly satisfies any role check). Users are a
module-level seed list, same synthetic-data pattern as resources.py — no DB.
See docs/superpowers/specs/2026-08-13-rbac-design.md for the full design.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time

import jwt
from fastapi import Depends, Header, HTTPException

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = "dev-only-insecure-secret-do-not-use-in-prod"
    logger.warning(
        "JWT_SECRET not set — falling back to a dev-only insecure default. "
        "Never rely on this outside local dev."
    )

JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 4 * 60 * 60  # 4 hours

ROLES = ("admin", "operator", "viewer")
AGENCIES = ("city_emergency_mgmt", "regional_health_dept")


def new_salt() -> str:
    return os.urandom(16).hex()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 100_000
    ).hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


def _seed_user(username: str, password: str, role: str, agency: str) -> dict:
    salt = new_salt()
    return {
        "username": username,
        "salt": salt,
        "password_hash": hash_password(password, salt),
        "role": role,
        "agency": agency,
    }


# Seed users: all 3 roles, across both agencies (real data for tracker 3.5's
# later agency-filtering work).
USERS: dict[str, dict] = {
    u["username"]: u
    for u in [
        _seed_user("alice_admin", "admin-pass", "admin", "city_emergency_mgmt"),
        _seed_user("bob_operator", "operator-pass", "operator", "city_emergency_mgmt"),
        _seed_user("carol_viewer", "viewer-pass", "viewer", "regional_health_dept"),
        _seed_user("dave_operator", "operator-pass2", "operator", "regional_health_dept"),
    ]
}


def authenticate(username: str, password: str) -> dict | None:
    user = USERS.get(username)
    if user is None:
        return None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return user


def issue_token(username: str, role: str, agency: str) -> str:
    payload = {
        "username": username,
        "role": role,
        "agency": agency,
        "exp": time.time() + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError (or a subclass, e.g. ExpiredSignatureError)
    on a tampered, malformed, or expired token."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: extracts + verifies the Bearer token. 401 on any
    missing/malformed/invalid/expired token — deliberately not
    fastapi.security.HTTPBearer, whose default auto_error raises 403 on a
    missing header (the endpoint matrix requires 401 for "no token")."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("Bearer "):]
    try:
        payload = verify_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return payload


_ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}


def require_role(*roles: str):
    """Dependency factory: 403 unless the current user's role rank is >= the
    lowest rank among `roles` — hierarchy is admin > operator > viewer, so
    e.g. require_role("viewer") also admits operator and admin (fixes a bug
    where an operator token got 403 on viewer+ routes; see
    docs/superpowers/specs/2026-08-13-rbac-design.md)."""
    min_rank = min(_ROLE_RANK[r] for r in roles)

    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if _ROLE_RANK.get(user["role"], -1) < min_rank:
            raise HTTPException(status_code=403, detail="insufficient role")
        return user

    return _checker
