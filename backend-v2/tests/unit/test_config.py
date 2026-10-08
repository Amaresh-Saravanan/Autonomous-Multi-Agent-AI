import pytest

from app.config import Settings


def test_development_fallback_secret_is_set():
    s = Settings(app_env="development", jwt_secret=None)
    assert s.jwt_secret


def test_production_without_secret_fails_safely():
    with pytest.raises(RuntimeError):
        Settings(app_env="production", jwt_secret=None)


def test_production_with_secret_succeeds():
    s = Settings(app_env="production", jwt_secret="real-secret")
    assert s.jwt_secret == "real-secret"


def test_cors_origins_list_parses_csv():
    s = Settings(cors_origins="http://a.com, http://b.com")
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]
