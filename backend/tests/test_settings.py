"""Tests for application settings loading (P5-01).

Tests cover: default values, environment variable overrides, YAML overrides,
type coercion, and validation errors for bad values.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.config import Settings, load_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "settings.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaultSettings:
    """load_settings() with no env vars or YAML returns sensible defaults."""

    def test_returns_settings_instance(self) -> None:
        settings = load_settings()
        assert isinstance(settings, Settings)

    def test_store_backend_default_memory(self) -> None:
        settings = load_settings()
        assert settings.store_backend == "memory"

    def test_database_url_defaults_sqlite(self) -> None:
        settings = load_settings()
        assert "sqlite" in settings.database_url

    def test_jwt_algorithm_default_hs256(self) -> None:
        settings = load_settings()
        assert settings.jwt_algorithm == "HS256"

    def test_jwt_expire_seconds_is_int(self) -> None:
        settings = load_settings()
        assert isinstance(settings.jwt_expire_seconds, int)
        assert settings.jwt_expire_seconds > 0

    def test_nonce_ttl_is_int(self) -> None:
        settings = load_settings()
        assert isinstance(settings.nonce_ttl_seconds, int)
        assert settings.nonce_ttl_seconds == 300

    def test_max_body_bytes_is_64k(self) -> None:
        settings = load_settings()
        assert settings.max_body_bytes == 65536

    def test_models_dir_is_path(self) -> None:
        settings = load_settings()
        assert isinstance(settings.models_dir, Path)

    def test_store_features_in_db_default_false(self) -> None:
        settings = load_settings()
        assert settings.store_features_in_db is False


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


class TestEnvVarOverrides:
    """Environment variables take precedence over defaults."""

    def test_store_backend_redis(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_BACKEND", "redis")
        settings = load_settings()
        assert settings.store_backend == "redis"

    def test_jwt_algorithm_rs256(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        settings = load_settings()
        assert settings.jwt_algorithm == "RS256"

    def test_nonce_ttl_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NONCE_TTL_SECONDS", "600")
        settings = load_settings()
        assert settings.nonce_ttl_seconds == 600

    def test_store_features_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_FEATURES_IN_DB", "true")
        settings = load_settings()
        assert settings.store_features_in_db is True

    def test_store_features_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_FEATURES_IN_DB", "1")
        settings = load_settings()
        assert settings.store_features_in_db is True

    def test_database_url_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/botguard")
        settings = load_settings()
        assert settings.database_url == "postgresql://user:pass@localhost/botguard"


# ---------------------------------------------------------------------------
# YAML overrides
# ---------------------------------------------------------------------------


class TestYamlOverrides:
    """YAML file values are used when the environment variable is not set."""

    def test_yaml_overrides_store_backend(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "store_backend: redis\n")
        settings = load_settings(yaml_path=p)
        assert settings.store_backend == "redis"

    def test_env_overrides_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variable beats YAML."""
        p = _write_yaml(tmp_path, "store_backend: redis\n")
        monkeypatch.setenv("STORE_BACKEND", "memory")
        settings = load_settings(yaml_path=p)
        assert settings.store_backend == "memory"

    def test_missing_yaml_path_is_ignored(self, tmp_path: Path) -> None:
        settings = load_settings(yaml_path=tmp_path / "nonexistent.yaml")
        assert settings.store_backend == "memory"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    """Invalid values raise ValueError."""

    def test_invalid_store_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_BACKEND", "dynamodb")
        with pytest.raises(ValueError, match="STORE_BACKEND"):
            load_settings()

    def test_invalid_jwt_algorithm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_ALGORITHM", "none")
        with pytest.raises(ValueError, match="JWT_ALGORITHM"):
            load_settings()

    def test_non_integer_nonce_ttl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NONCE_TTL_SECONDS", "five-hundred")
        with pytest.raises(ValueError, match="NONCE_TTL_SECONDS"):
            load_settings()

    def test_invalid_bool_store_features(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_FEATURES_IN_DB", "maybe")
        with pytest.raises(ValueError, match="STORE_FEATURES_IN_DB"):
            load_settings()
