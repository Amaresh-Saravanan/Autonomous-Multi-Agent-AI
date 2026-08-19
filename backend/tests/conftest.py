"""Pytest configuration and fixtures for the backend test suite.

Autouse fixture: monkeypatch geocoding to always return (None, None), forcing
all tests down the fallback path (unchanged distance+time clustering) without
hitting the real Nominatim API. Individual tests override this fixture locally
to test district-clustering behavior with canned geocode responses.
"""
import pytest
from app import geocode


@pytest.fixture(autouse=True)
def _no_real_geocoding(monkeypatch):
    """Force all tests to use the fallback distance+time clustering logic
    without hitting the real Nominatim API."""
    monkeypatch.setattr(geocode, "reverse", lambda lat, lon: (None, None))
