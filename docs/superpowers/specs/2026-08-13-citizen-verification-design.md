# Citizen Report Ingestion + Trust/Verification — Design

**Date:** 2026-08-13
**Tracker item:** 3.3 (`docs/MIGRATION_TRACKER.md`)
**Status:** approved

## Problem

Citizen reports (SMS/app free-text-adjacent claims like "flooding is severe
here") are a named source type in `Event.source_type`'s docstring
(`satellite|drone|iot|weather|social|gis|citizen`) but have no normalizer.
PRD SEC-4 asks for a trust/verification pipeline so an unverified citizen
claim doesn't get treated the same as a calibrated sensor reading.

## Judgment call: citizen reports do not wake the orchestrator

A citizen report is scored for trust against the incident's current AG-1
severity and stored as an `Event` with a computed `confidence` — but it does
**not** run through `orchestrator.run()`, does not trigger any agent, and is
not pushed to `/ws/alerts`. `POST /ingest/citizen` normalizes and returns the
`Event` only.

Why:
- **Trigger routing invariant.** `tests/test_trigger_routing.py` asserts
  exact agent-id sets per source_type. No agent's `triggers` frozenset
  contains `"citizen"` (confirmed: `base.py` default is
  `{"iot","weather","satellite"}`, and `damage`/`rescue`/`medical`/
  `allocation`/`route` narrow it further to subsets of that). Keeping
  citizen reports out of the orchestrator chain entirely means that file
  needs zero changes and its assertions stay exactly as-is — a citizen
  report can't accidentally wake AG-1..AG-8 today or after a careless
  future edit, because there's no code path connecting `/ingest/citizen`
  to `orchestrator.run()` at all.
- **A single unverified claim isn't evidence.** The whole point of scoring
  trust is to decide whether a report is corroborating enough to matter;
  short-circuiting straight into agent recommendations before that
  judgment exists would undercut the verification step.
- **Avoids collision with AG-7.** `agents/citizen.py` (AG-7, citizen chat)
  is a separate, already-shipped feature invoked directly from
  `/citizen/chat`. This work does not touch that file.

Upgrade path: once corroborated citizen reports should actually influence
AG-1's severity (e.g. multiple high-confidence reports in the same grid
cell), add an explicit, separate ingestion path that folds them into the
severity grid — don't repurpose the orchestrator's `triggers` mechanism for
it, since citizen reports are corroboration, not primary sensor evidence.

## Design

### New module: `backend/app/citizen_verification.py`

```python
CORROBORATING_THRESHOLD = 0.2
DIVERGENT_THRESHOLD = 0.4
NEUTRAL_CONFIDENCE = 0.5
CORROBORATING_CONFIDENCE = 0.8
DIVERGENT_CONFIDENCE = 0.2

def score_confidence(incident_id, claimed_severity, blackboard_state) -> tuple[float, bool]:
    ...
```

Pure function: takes the blackboard state dict already fetched by the
caller (no `blackboard.get` call inside it), so it has zero dependency on
`app.blackboard` and no circular-import risk with `normalizers.py`.

Logic:
- No prior `AG-1` state (`blackboard_state.get("AG-1", {}).get("severity")`
  is `None`) → nothing to corroborate against yet → `(NEUTRAL_CONFIDENCE,
  False)`.
- `abs(claimed_severity - ag1_severity) <= CORROBORATING_THRESHOLD` →
  `(CORROBORATING_CONFIDENCE, False)`.
- `abs(diff) > DIVERGENT_THRESHOLD` → `(DIVERGENT_CONFIDENCE, True)`.
- Middle band (`0.2 < diff <= 0.4`) → neutral, not flagged. No test covers
  this band explicitly; it's the reasonable default for "neither clearly
  corroborating nor clearly divergent."

Threshold choice: mirrors the existing style of named-constant heuristics
in this repo (`agents/damage.py`'s `POP_DENSITY_PER_KM2`). 0.2 and 0.4 are
round numbers on the 0..1 severity scale wide enough that GPS/human
severity-perception noise doesn't get misflagged as divergent, narrow
enough that a citizen claiming "minor" (0.1) against an AG-1 "severe" (0.8)
still gets flagged.

`ponytail:` simple threshold comparison on a structured `claimed_severity`
float, not real NLP claim-extraction from free-text reports; upgrade when
citizen reports need free-text severity parsing (e.g. inferring severity
from a message body instead of a pre-filled slider/field).

### `backend/app/normalizers.py`

Add `normalize_citizen(raw)`: pulls `incident_id` from `raw` with the same
`"default"` fallback `main.py`'s `/ingest` handler uses (normalizers never
see the handler's separately-parsed `incident_id`, so this has to be
independently consistent), calls `blackboard.get(incident_id)`, scores
confidence via `citizen_verification.score_confidence`, and sets it as
`Event.confidence`. Flags go into `Event.payload["flagged_for_review"]`.
Registered under `NORMALIZERS["citizen"]`.

Import `from . import blackboard` — safe, since `blackboard.py` has no
imports from `normalizers.py` or `app` (only `json`/`os`).

## Testing

New `backend/tests/test_citizen_verification.py`:
1. `normalize_citizen` returns `Event` with `source_type="citizen"`.
2. Corroborating: seed `AG-1` severity 0.6, claim 0.65 → confidence >= 0.7.
3. Divergent: seed `AG-1` severity 0.6, claim 0.1 → confidence <= 0.3,
   `flagged_for_review` True.
4. No prior state: fresh incident_id → neutral confidence, not flagged.
5. Integration: `POST /ingest/citizen` via `TestClient` → 200, and
   `recommendations == []` (the tripwire that proves no agent woke up).

Regression: `tests/test_trigger_routing.py`'s 3 existing tests run
unchanged and must stay green — proof this item didn't touch dispatch
routing.
