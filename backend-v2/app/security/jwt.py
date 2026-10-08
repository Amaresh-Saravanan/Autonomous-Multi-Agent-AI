"""JWT encode/decode (Phase 6)."""

from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings
from app.errors import AuthenticationError


def create_access_token(*, subject: str, role: str, agency_id: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "agency_id": agency_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc
