# backend-v2

Clean reimplementation of the backend. `../backend/` stays as the reference until
this reaches parity; port behavior from it deliberately, not by copy-paste.
Requirements live in `../docs/PRD.md`.

    python -m pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8001
    python -m pytest tests/ -v

First run (creates agencies, an ADMIN user, citizen + iot devices; idempotent):

    alembic upgrade head
    SEED_ADMIN_EMAIL=you@agency.org python -m app.seed      # prints generated secrets once

See `../docs/DEPLOYMENT.md` for the full deployment guide.
