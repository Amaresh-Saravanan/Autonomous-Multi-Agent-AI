# backend-v2

Clean reimplementation of the backend. `../backend/` stays as the reference until
this reaches parity; port behavior from it deliberately, not by copy-paste.
Requirements live in `../docs/PRD.md`.

    python -m pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8001
    python -m pytest tests/ -v
