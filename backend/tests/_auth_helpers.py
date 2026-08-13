"""Shared test-only helper for building auth headers (tracker 3.4). Builds
tokens directly via app.auth.issue_token — no need to round-trip through
POST /auth/login in every test file; that round-trip is exercised for real
in test_auth.py, which is the thing actually testing login.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import auth


def viewer_headers() -> dict:
    return {"Authorization": f"Bearer {auth.issue_token('carol_viewer', 'viewer', 'regional_health_dept')}"}


def operator_headers() -> dict:
    return {"Authorization": f"Bearer {auth.issue_token('bob_operator', 'operator', 'city_emergency_mgmt')}"}


def admin_headers() -> dict:
    return {"Authorization": f"Bearer {auth.issue_token('alice_admin', 'admin', 'city_emergency_mgmt')}"}
