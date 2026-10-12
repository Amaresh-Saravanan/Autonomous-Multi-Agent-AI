"""RBAC + agency isolation (Phase 6). Enforced here, in the backend
dependency/service layer — never in the frontend."""

import uuid

from fastapi import Depends

from app.errors import AuthorizationError
from app.models.security import RoleEnum, User
from app.security.auth import require_user

ROLE_RANK = {RoleEnum.VIEWER: 0, RoleEnum.OPERATOR: 1, RoleEnum.ADMIN: 2}

ROLE_PERMISSIONS: dict[RoleEnum, set[str]] = {
    RoleEnum.VIEWER: {"view_resources", "view_incidents", "view_recommendations", "view_alerts"},
    RoleEnum.OPERATOR: {
        "view_resources", "view_incidents", "view_recommendations", "view_alerts",
        "approve_recommendation", "reject_recommendation", "submit_citizen_chat",
    },
    RoleEnum.ADMIN: {
        "view_resources", "view_incidents", "view_recommendations", "view_alerts",
        "approve_recommendation", "reject_recommendation", "submit_citizen_chat",
        "override_recommendation", "view_audit", "manage_devices", "manage_users",
    },
}


def require_role(minimum: RoleEnum):
    def dependency(user: User = Depends(require_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise AuthorizationError(f"Requires role >= {minimum.value}")
        return user

    return dependency


def require_permission(code: str):
    def dependency(user: User = Depends(require_user)) -> User:
        if code not in ROLE_PERMISSIONS.get(user.role, set()):
            raise AuthorizationError(f"Missing permission: {code}")
        return user

    return dependency


def require_agency_access(user: User, resource_agency_id: uuid.UUID | None) -> None:
    """Service-layer check: a user may only touch their own agency's data,
    unless they are ADMIN. A resource with no agency (`None`) is NOT
    implicitly visible to everyone — this fixes V1's `target_agency=NULL`
    leak. Callers needing "global" visibility must say so explicitly."""
    if user.role == RoleEnum.ADMIN:
        return
    if resource_agency_id is None or resource_agency_id != user.agency_id:
        raise AuthorizationError("Not authorized for this agency's data")
