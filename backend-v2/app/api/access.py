"""Access requests (SEC-1 stays admin-controlled; this makes the hand-off real).

* `request` / `reset-request` are submitted by the Next server-side proxy
  (citizen device credential), never directly by browsers. They always return
  the same generic acknowledgement, so they cannot be used to discover which
  emails have accounts.
* Only an ADMIN can list, approve or reject. Approving issues a one-time
  temporary password (shown once to the admin, who passes it on out-of-band —
  no email service is assumed) and forces a password change at first login."""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError, ValidationError
from app.infrastructure.database import get_db
from app.models.access import AccessRequest, AccessRequestKind, AccessRequestStatus
from app.models.audit import ActorTypeEnum
from app.models.security import Agency, Device, RoleEnum, User
from app.security.auth import hash_password
from app.security.devices import require_device
from app.security.permissions import require_role
from app.services.audit_service import record as audit_record

router = APIRouter(prefix="/api/v1/access", tags=["access"])

MAX_PENDING = 200  # hard cap so a flood of requests cannot bury real ones
GENERIC_ACK = {"status": "received"}


class SignupRequestBody(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    agency_text: str | None = Field(default=None, max_length=200)
    requested_role: RoleEnum | None = None


class ResetRequestBody(BaseModel):
    email: EmailStr


class ApproveBody(BaseModel):
    agency_id: uuid.UUID | None = None  # required for SIGNUP
    role: RoleEnum | None = None  # defaults to the requested role, else VIEWER


def _pending_count(db: Session) -> int:
    return db.scalar(
        select(func.count(AccessRequest.id)).where(AccessRequest.status == AccessRequestStatus.PENDING)
    ) or 0


def _has_pending(db: Session, kind: AccessRequestKind, email: str) -> bool:
    return db.scalars(
        select(AccessRequest).where(
            AccessRequest.kind == kind,
            AccessRequest.status == AccessRequestStatus.PENDING,
            AccessRequest.email == email,
        )
    ).first() is not None


@router.post("/request", status_code=202)
def request_access(
    body: SignupRequestBody, db: Session = Depends(get_db), device: Device = Depends(require_device("citizen"))
) -> dict:
    email = body.email.lower()
    exists = db.query(User).filter(func.lower(User.email) == email).first() is not None
    if not exists and not _has_pending(db, AccessRequestKind.SIGNUP, email) and _pending_count(db) < MAX_PENDING:
        # Never self-assign ADMIN: an admin picks the final role on approval.
        requested = body.requested_role if body.requested_role != RoleEnum.ADMIN else None
        db.add(AccessRequest(
            kind=AccessRequestKind.SIGNUP, email=email, full_name=body.full_name.strip(),
            agency_text=(body.agency_text or "").strip() or None,
            requested_role=requested.value if requested else None,
        ))
        db.commit()
    return GENERIC_ACK


@router.post("/reset-request", status_code=202)
def request_reset(
    body: ResetRequestBody, db: Session = Depends(get_db), device: Device = Depends(require_device("citizen"))
) -> dict:
    email = body.email.lower()
    user = db.query(User).filter(func.lower(User.email) == email, User.is_active.is_(True)).first()
    if user and not _has_pending(db, AccessRequestKind.RESET, email) and _pending_count(db) < MAX_PENDING:
        db.add(AccessRequest(kind=AccessRequestKind.RESET, email=email))
        db.commit()
    return GENERIC_ACK  # identical whether or not the account exists


def _serialize(r: AccessRequest) -> dict:
    return {
        "id": str(r.id), "kind": r.kind.value, "status": r.status.value, "email": r.email,
        "full_name": r.full_name, "agency_text": r.agency_text, "requested_role": r.requested_role,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
    }


@router.get("/requests")
def list_requests(
    status: AccessRequestStatus | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.ADMIN)),
) -> list[dict]:
    stmt = select(AccessRequest)
    if status is not None:
        stmt = stmt.where(AccessRequest.status == status)
    return [_serialize(r) for r in db.scalars(stmt.order_by(AccessRequest.created_at.desc()).limit(500))]


@router.get("/agencies")
def list_agencies(db: Session = Depends(get_db), admin: User = Depends(require_role(RoleEnum.ADMIN))) -> list[dict]:
    return [{"id": str(a.id), "name": a.name} for a in db.scalars(select(Agency).order_by(Agency.name))]


def _get_pending(db: Session, request_id: uuid.UUID) -> AccessRequest:
    req = db.get(AccessRequest, request_id)
    if req is None:
        raise NotFoundError("Access request not found")
    if req.status != AccessRequestStatus.PENDING:
        raise ValidationError(f"Request already {req.status.value.lower()}")
    return req


@router.post("/requests/{request_id}/approve")
def approve(
    request_id: uuid.UUID,
    body: ApproveBody,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(RoleEnum.ADMIN)),
) -> dict:
    req = _get_pending(db, request_id)
    temp_password = secrets.token_urlsafe(12)
    existing = db.query(User).filter(func.lower(User.email) == req.email).first()

    if req.kind == AccessRequestKind.SIGNUP:
        if existing is not None:
            raise ValidationError("An account with this email already exists")
        if body.agency_id is None or db.get(Agency, body.agency_id) is None:
            raise ValidationError("Choose a valid agency for the new account")
        role = body.role or (RoleEnum(req.requested_role) if req.requested_role else RoleEnum.VIEWER)
        user = User(
            email=req.email, hashed_password=hash_password(temp_password), role=role,
            agency_id=body.agency_id, must_change_password=True,
        )
        db.add(user)
        agency_id, action = body.agency_id, "access_signup_approved"
    else:
        if existing is None or not existing.is_active:
            raise ValidationError("No active account for this email")
        existing.hashed_password = hash_password(temp_password)
        existing.must_change_password = True
        agency_id, action = existing.agency_id, "access_reset_approved"

    req.status = AccessRequestStatus.APPROVED
    req.decided_by_user_id = admin.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    audit_record(
        db, actor_type=ActorTypeEnum.USER, actor_id=admin.email, action=action, agency_id=agency_id,
        metadata={"request_id": str(req.id), "email": req.email},
    )
    return {"email": req.email, "temporary_password": temp_password, "must_change_password": True}


@router.post("/requests/{request_id}/reject")
def reject(
    request_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_role(RoleEnum.ADMIN))
) -> dict:
    req = _get_pending(db, request_id)
    req.status = AccessRequestStatus.REJECTED
    req.decided_by_user_id = admin.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    audit_record(
        db, actor_type=ActorTypeEnum.USER, actor_id=admin.email, action="access_request_rejected",
        metadata={"request_id": str(req.id), "email": req.email, "kind": req.kind.value},
    )
    return _serialize(req)
