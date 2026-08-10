"""In-memory resource registry (PRD AG-3/4/5/6 inputs). Synthetic seed data —
Postgres persistence is Phase 3; this is enough to prove agent reasoning now.
"""
from __future__ import annotations

HOSPITALS = [
    {"id": "h-1", "name": "Coastal General", "lat": 13.05, "lon": 80.28, "capacity": 120, "free_beds": 8},
    {"id": "h-2", "name": "City General", "lat": 13.09, "lon": 80.25, "capacity": 200, "free_beds": 45},
    {"id": "h-3", "name": "St. Mary's", "lat": 13.02, "lon": 80.22, "capacity": 80, "free_beds": 20},
]

SHELTERS = [
    {"id": "s-1", "name": "Community Hall A", "lat": 13.07, "lon": 80.26, "capacity": 300, "occupied": 40},
    {"id": "s-2", "name": "School Ground B", "lat": 13.04, "lon": 80.29, "capacity": 500, "occupied": 120},
]

TEAMS = [
    {"id": "t-1", "name": "Rescue Team Alpha", "lat": 13.06, "lon": 80.27, "status": "available"},
    {"id": "t-2", "name": "Rescue Team Bravo", "lat": 13.10, "lon": 80.24, "status": "available"},
    {"id": "t-3", "name": "Rescue Team Charlie", "lat": 13.01, "lon": 80.23, "status": "deployed"},
]

AMBULANCES = [
    {"id": "amb-1", "lat": 13.05, "lon": 80.28, "status": "available"},
    {"id": "amb-2", "lat": 13.08, "lon": 80.25, "status": "available"},
]

SUPPLIES = {"food_units": 5000, "water_liters": 20000, "blankets": 1500}
