# RBAC: JWT Auth + In-Memory Users — Design

**Date:** 2026-08-13
**Tracker item:** 3.4 (`docs/MIGRATION_TRACKER.md`)
**Status:** approved

## Problem

Every state-changing endpoint is wide open, and `_decide()` (approve/reject)
audits every decision under a fixed `"operator"` string (`ponytail:` in
`app/main.py`, decisions log 2026-08-06) — there's no real identity behind a
decision, and no gating at all on who can read incident state or make one.
SEC-1 requires role-based access; this is the minimum that satisfies it.

## Roles

Three: `admin`, `operator`, `viewer`. No finer grading (e.g. per-agency admin,
read-only-audit) — nothing in the PRD or current dashboard UI distinguishes
more than "can decide," "can only look," and "can do everything including
decide." Add a role when a real use case needs one, not speculatively.
`admin` implicitly satisfies any role check (superset, not a separate
permission list).

## Agencies

Two synthetic values, matching `resources.py`'s seed-data flavor:
`"city_emergency_mgmt"`, `"regional_health_dept"`. Exist now so 3.5
(multi-agency dashboard views/scoping) has real, non-uniform data to filter
against — not used for access control in this item.

## Endpoint → required-role matrix

| Endpoint | Requirement |
|---|---|
| `POST /auth/login` | open |
| `GET /health` | open |
| `POST /ingest/{source_type}` | open (unauthenticated sensors/citizens) |
| `POST /citizen/chat` | open (citizens aren't platform users) |
| `GET /incidents/{id}`, `GET /incidents/{id}/severity`, `GET /recommendations`, `GET /resources` | any authenticated role (viewer+) |
| `POST /recommendations/{id}/approve`, `POST /recommendations/{id}/reject` | operator+ |
| `GET /metrics` | operator+ |

## Users

`app/auth.py` seeds a module-level `USERS` list of dicts (same shape as
`resources.py`'s `HOSPITALS`/`SHELTERS` — no DB), covering all 3 roles across
both agencies: an admin, an operator, and a viewer, plus a second operator in
the other agency so 3.5 has cross-agency data. Each entry: `username`,
`password_hash`, `salt`, `role`, `agency`.

## Password hashing

Stdlib `hashlib.pbkdf2_hmac("sha256", password, salt, iterations)` with a
random per-user salt (`os.urandom`), no new dependency. Verification
recomputes the hash with the stored salt and compares with
`hmac.compare_digest` (constant-time — avoids a timing side-channel on the
one place this app checks a secret against user input).

## JWT

`pyjwt` (added to `requirements.txt`), not `python-jose` — smaller
dependency, does the one thing needed (encode/decode + expiry validation),
no extra crypto backends to pull in. Token payload: `username`, `role`,
`agency`, `exp` (4 hours from issue). Signed HS256 with `JWT_SECRET`.

`JWT_SECRET` sourcing: `os.getenv("JWT_SECRET", "dev-only-insecure-secret-do-not-use-in-prod")`,
with a `logging.warning(...)` fired once at module import time if the env
var is unset — loud in logs rather than silently running production on a
guessable key. `.env.example` already documents this (tracker 3.6).

`get_current_user` reads the `Authorization: Bearer <token>` header directly
(not `fastapi.security.HTTPBearer`, whose default `auto_error=True` raises
403 on a missing header) — the matrix requires 401 for "no/bad token" and
403 only for "authenticated but wrong role," so the header is parsed by hand
and a missing/malformed/invalid/expired token raises `HTTPException(401)`.
`require_role(*roles)` wraps it and raises `HTTPException(403)` when the
user's role (unless `admin`) isn't in the allowed set.

## Out of scope (this item)

Agency-based data scoping/filtering (3.5), refresh tokens, logout/revocation,
password reset, persistent user store (Postgres is Phase 3 generally, not
special-cased here) — none of these have a concrete need yet.
