import pytest

from app.config import Settings


def test_development_fallback_secret_is_set():
    s = Settings(app_env="development", jwt_secret=None)
    assert s.jwt_secret


def test_production_without_secret_fails_safely():
    with pytest.raises(RuntimeError):
        Settings(app_env="production", jwt_secret=None)


def test_production_with_secret_succeeds():
    secret = "a-genuinely-random-secret-of-32+-chars"
    s = Settings(app_env="production", jwt_secret=secret)
    assert s.jwt_secret == secret


def test_cors_origins_list_parses_csv():
    s = Settings(cors_origins="http://a.com, http://b.com")
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]


def test_production_rejects_weak_or_placeholder_jwt_secret(monkeypatch):
    import pytest
    from app.config import Settings

    for bad in ("short", "change-me-in-production-please-make-it-long"):
        with pytest.raises(RuntimeError, match="at least 32"):
            Settings(app_env="production", jwt_secret=bad)
    assert Settings(app_env="production", jwt_secret="x" * 40).jwt_secret == "x" * 40
