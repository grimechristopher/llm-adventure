# tests/core/test_settings.py
import pytest
from pydantic import ValidationError

def test_settings_loads_from_env(monkeypatch):
    """Test settings loads required environment variables"""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    from config.settings import Settings
    test_settings = Settings()

    assert test_settings.database_url == "postgresql+asyncpg://test:test@localhost/test"
    assert test_settings.secret_key.get_secret_value() == "test-secret-key"
    assert test_settings.log_level == "INFO"

def test_settings_fails_without_required_vars(monkeypatch):
    """Test settings validation fails when required vars missing"""
    # Clear environment variables and disable .env file loading
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        from config.settings import Settings
        Settings(_env_file=None)
