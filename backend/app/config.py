"""Backend configuration loading and validation.

Settings are read from environment variables first; a YAML config file may
supply defaults for any key that is not set in the environment.  The rule
configuration (enabled flags and weights per rule) lives in a separate
``rules.yaml`` and is loaded via :func:`load_rule_config`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.rules import DEFAULT_RULE_WEIGHTS

# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, object] = {
    # Store backend: "memory" (default, for dev/tests) or "redis"
    "STORE_BACKEND": "memory",
    # Redis connection URL (only used when STORE_BACKEND=redis)
    "REDIS_URL": "redis://localhost:6379/0",
    # SQLAlchemy database URL (default in-process SQLite)
    "DATABASE_URL": "sqlite:///./botguard.db",
    # HMAC secret for HS256 JWT signing (must be set in production)
    "JWT_SECRET": "change-me-in-production",
    # JWT algorithm: HS256 | RS256 | ES256
    "JWT_ALGORITHM": "HS256",
    # Path to PEM-encoded private key file (RS256/ES256 only)
    "JWT_PRIVATE_KEY_FILE": "",
    # Path to PEM-encoded public key file (RS256/ES256 only, for verification)
    "JWT_PUBLIC_KEY_FILE": "",
    # JWT issuer claim
    "JWT_ISSUER": "botguard",
    # JWT audience claim
    "JWT_AUDIENCE": "botguard-portal",
    # JWT token lifetime in seconds
    "JWT_EXPIRE_SECONDS": "90",
    # Path to the backend/models directory
    "MODELS_DIR": str(Path(__file__).resolve().parents[1] / "models"),
    # Path to backend/config/rules.yaml
    "RULES_CONFIG_FILE": str(Path(__file__).resolve().parents[1] / "config" / "rules.yaml"),
    # Path to backend/config/policy.yaml
    "POLICY_CONFIG_FILE": str(Path(__file__).resolve().parents[1] / "config" / "policy.yaml"),
    # Nonce TTL in seconds (single-use, bound to context hash)
    "NONCE_TTL_SECONDS": "300",
    # Rate-limit: max nonce requests per IP bucket per minute
    "RATE_LIMIT_NONCE_PER_MIN": "60",
    # Rate-limit: max assess requests per IP bucket per minute
    "RATE_LIMIT_ASSESS_PER_MIN": "30",
    # Max request body size in bytes (64 KB)
    "MAX_BODY_BYTES": "65536",
    # Enable optional feature storage in the DB (TTL-limited)
    "STORE_FEATURES_IN_DB": "false",
    # Feature storage TTL in seconds (7 days)
    "FEATURE_TTL_SECONDS": str(7 * 24 * 3600),
    # Assessment long-term TTL in seconds (30 days)
    "ASSESSMENT_TTL_SECONDS": str(30 * 24 * 3600),
}


@dataclass(frozen=True)
class Settings:
    """Validated application settings."""

    store_backend: str  # "memory" | "redis"
    redis_url: str
    database_url: str

    jwt_secret: str
    jwt_algorithm: str  # "HS256" | "RS256" | "ES256"
    jwt_private_key_file: str
    jwt_public_key_file: str
    jwt_issuer: str
    jwt_audience: str
    jwt_expire_seconds: int

    models_dir: Path
    rules_config_file: Path
    policy_config_file: Path

    nonce_ttl_seconds: int
    rate_limit_nonce_per_min: int
    rate_limit_assess_per_min: int
    max_body_bytes: int

    store_features_in_db: bool
    feature_ttl_seconds: int
    assessment_ttl_seconds: int

    def jwt_private_key(self) -> str | None:
        """Return the PEM private key string, or None if not configured."""
        if self.jwt_private_key_file:
            return Path(self.jwt_private_key_file).read_text(encoding="utf-8")
        return None

    def jwt_public_key(self) -> str | None:
        """Return the PEM public key string, or None if not configured."""
        if self.jwt_public_key_file:
            return Path(self.jwt_public_key_file).read_text(encoding="utf-8")
        return None


def _str(val: object) -> str:
    return str(val)


def _int(val: object, name: str) -> int:
    try:
        return int(str(val))
    except ValueError as exc:
        raise ValueError(f"setting {name} must be an integer, got {val!r}") from exc


def _bool(val: object, name: str) -> bool:
    s = str(val).lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"setting {name} must be a boolean-like value, got {val!r}")


def load_settings(yaml_path: Path | None = None) -> Settings:
    """Load settings from environment variables, with optional YAML defaults.

    Environment variables take precedence over YAML values, which in turn
    take precedence over the built-in defaults above.

    Args:
        yaml_path: Optional path to a YAML config file.  Only keys that
            correspond to known setting names are read; unknown keys are
            ignored.

    Returns:
        A frozen :class:`Settings` instance.

    Raises:
        ValueError: If any value cannot be coerced to the required type.
    """
    yaml_vals: dict[str, object] = {}
    if yaml_path and yaml_path.exists():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            yaml_vals = {k.upper(): v for k, v in raw.items()}

    def get(name: str) -> object:
        """Resolve a setting in env > yaml > defaults order."""
        if name in os.environ:
            return os.environ[name]
        if name in yaml_vals:
            return yaml_vals[name]
        return _DEFAULTS[name]

    store_backend = _str(get("STORE_BACKEND")).lower()
    if store_backend not in ("memory", "redis"):
        raise ValueError(f"STORE_BACKEND must be 'memory' or 'redis', got {store_backend!r}")

    jwt_algorithm = _str(get("JWT_ALGORITHM")).upper()
    if jwt_algorithm not in ("HS256", "RS256", "ES256"):
        raise ValueError(f"JWT_ALGORITHM must be HS256, RS256 or ES256, got {jwt_algorithm!r}")

    return Settings(
        store_backend=store_backend,
        redis_url=_str(get("REDIS_URL")),
        database_url=_str(get("DATABASE_URL")),
        jwt_secret=_str(get("JWT_SECRET")),
        jwt_algorithm=jwt_algorithm,
        jwt_private_key_file=_str(get("JWT_PRIVATE_KEY_FILE")),
        jwt_public_key_file=_str(get("JWT_PUBLIC_KEY_FILE")),
        jwt_issuer=_str(get("JWT_ISSUER")),
        jwt_audience=_str(get("JWT_AUDIENCE")),
        jwt_expire_seconds=_int(get("JWT_EXPIRE_SECONDS"), "JWT_EXPIRE_SECONDS"),
        models_dir=Path(_str(get("MODELS_DIR"))),
        rules_config_file=Path(_str(get("RULES_CONFIG_FILE"))),
        policy_config_file=Path(_str(get("POLICY_CONFIG_FILE"))),
        nonce_ttl_seconds=_int(get("NONCE_TTL_SECONDS"), "NONCE_TTL_SECONDS"),
        rate_limit_nonce_per_min=_int(get("RATE_LIMIT_NONCE_PER_MIN"), "RATE_LIMIT_NONCE_PER_MIN"),
        rate_limit_assess_per_min=_int(
            get("RATE_LIMIT_ASSESS_PER_MIN"), "RATE_LIMIT_ASSESS_PER_MIN"
        ),
        max_body_bytes=_int(get("MAX_BODY_BYTES"), "MAX_BODY_BYTES"),
        store_features_in_db=_bool(get("STORE_FEATURES_IN_DB"), "STORE_FEATURES_IN_DB"),
        feature_ttl_seconds=_int(get("FEATURE_TTL_SECONDS"), "FEATURE_TTL_SECONDS"),
        assessment_ttl_seconds=_int(get("ASSESSMENT_TTL_SECONDS"), "ASSESSMENT_TTL_SECONDS"),
    )


# ---------------------------------------------------------------------------
# Rule configuration (pre-existing, preserved from Phase 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleConfig:
    """Validated enabled flags and weights for the environment rules."""

    enabled: dict[str, bool]
    weights: dict[str, float]


def load_rule_config(path: Path) -> RuleConfig:
    """Load and validate a rules YAML file.

    Args:
        path: Path to ``rules.yaml``.

    Returns:
        A frozen :class:`RuleConfig` instance.

    Raises:
        ValueError: If the file cannot be read or contains invalid values.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"unable to read rule configuration: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("rules"), dict):
        raise ValueError("rule configuration must contain a rules mapping")

    enabled: dict[str, bool] = {}
    weights: dict[str, float] = {}
    for rule_id, defaults in raw["rules"].items():
        if rule_id not in DEFAULT_RULE_WEIGHTS:
            raise ValueError(f"unknown rule ID: {rule_id}")
        if not isinstance(defaults, dict):
            raise ValueError(f"configuration for {rule_id} must be a mapping")
        is_enabled = defaults.get("enabled", True)
        configured_weight = defaults.get("weight", DEFAULT_RULE_WEIGHTS[rule_id])
        if not isinstance(is_enabled, bool):
            raise ValueError(f"enabled flag for {rule_id} must be boolean")
        if not isinstance(configured_weight, (int, float)) or not 0 <= configured_weight <= 1:
            raise ValueError(f"weight for {rule_id} must be in [0, 1]")
        enabled[rule_id] = is_enabled
        weights[rule_id] = float(configured_weight)

    for rule_id, default_weight in DEFAULT_RULE_WEIGHTS.items():
        enabled.setdefault(rule_id, True)
        weights.setdefault(rule_id, default_weight)
    return RuleConfig(enabled=enabled, weights=weights)
