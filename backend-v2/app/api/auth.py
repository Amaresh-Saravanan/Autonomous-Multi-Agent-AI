from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models.security import User
from app.errors import AuthenticationError, ValidationError
from app.models.audit import ActorTypeEnum
from app.schemas.auth import ChangePasswordRequest, LoginRequest, MeResponse, TokenResponse
from app.security.auth import (
    authenticate_user,
    hash_password,
    require_user_allow_password_change,
    verify_password,
)
from app.services.audit_service import record as audit_record
from app.security.jwt import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, body.email, body.password)
    token = create_access_token(
        subject=str(user.id), role=user.role.value, agency_id=str(user.agency_id)
    )
    return TokenResponse(
        access_token=token,
        role=user.role.value,
        agency_id=str(user.agency_id),
        agency_name=user.agency.name if user.agency else None,
        email=user.email,
        must_change_password=user.must_change_password,
    )


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(require_user_allow_password_change)) -> MeResponse:
    """Session check: lets the frontend (and its server-side proxies) verify
    a bearer token and learn the caller's role without trusting the JWT
    payload client-side."""
    return MeResponse(
        email=user.email,
        role=user.role.value,
        agency_id=str(user.agency_id),
        agency_name=user.agency.name if user.agency else None,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_allow_password_change),
) -> None:
    if not verify_password(body.current_password, user.hashed_password):
        raise AuthenticationError("Current password is incorrect")
    if body.new_password == body.current_password:
        raise ValidationError("New password must differ from the current one")
    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    audit_record(
        db, actor_type=ActorTypeEnum.USER, actor_id=user.email, action="password_changed", agency_id=user.agency_id
    )
