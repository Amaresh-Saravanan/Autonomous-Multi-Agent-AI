import uuid

import pytest

from app.errors import AuthorizationError
from app.models.security import RoleEnum
from app.security.permissions import ROLE_PERMISSIONS, require_agency_access


class _FakeUser:
    def __init__(self, role, agency_id):
        self.role = role
        self.agency_id = agency_id


def test_viewer_cannot_approve_but_operator_can():
    assert "approve_recommendation" not in ROLE_PERMISSIONS[RoleEnum.VIEWER]
    assert "approve_recommendation" in ROLE_PERMISSIONS[RoleEnum.OPERATOR]


def test_only_admin_can_override():
    assert "override_recommendation" not in ROLE_PERMISSIONS[RoleEnum.OPERATOR]
    assert "override_recommendation" in ROLE_PERMISSIONS[RoleEnum.ADMIN]


def test_agency_access_same_agency_allowed():
    agency_id = uuid.uuid4()
    user = _FakeUser(RoleEnum.OPERATOR, agency_id)
    require_agency_access(user, agency_id)  # does not raise


def test_agency_access_cross_agency_denied():
    user = _FakeUser(RoleEnum.OPERATOR, uuid.uuid4())
    with pytest.raises(AuthorizationError):
        require_agency_access(user, uuid.uuid4())


def test_agency_access_null_target_not_implicitly_visible():
    user = _FakeUser(RoleEnum.OPERATOR, uuid.uuid4())
    with pytest.raises(AuthorizationError):
        require_agency_access(user, None)


def test_admin_bypasses_agency_check():
    user = _FakeUser(RoleEnum.ADMIN, uuid.uuid4())
    require_agency_access(user, None)
    require_agency_access(user, uuid.uuid4())
