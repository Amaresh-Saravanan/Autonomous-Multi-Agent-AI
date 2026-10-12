"""Password hashing + persistent-user authentication + `require_user`
dependency (Phase 6). Replaces V1's hardcoded user list."""

import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.errors import AuthenticationError
from app.infrastructure.database import get_db
from app.models.security import User
from app.security.jwt import decode_access_token

_hasher = PasswordHasher()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    return user


def require_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise AuthenticationError("Missing bearer token")
    payload = decode_access_token(token)
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user
