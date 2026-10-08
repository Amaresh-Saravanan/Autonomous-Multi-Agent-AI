from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.security.auth import authenticate_user
from app.security.jwt import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, body.email, body.password)
    token = create_access_token(
        subject=str(user.id), role=user.role.value, agency_id=str(user.agency_id)
    )
    return TokenResponse(access_token=token, role=user.role.value, agency_id=str(user.agency_id))
