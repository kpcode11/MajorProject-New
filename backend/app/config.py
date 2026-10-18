"""Backend configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.rules import DEFAULT_RULE_WEIGHTS


@dataclass(frozen=True)
class RuleConfig:
    """Validated enabled flags and weights for the environment rules."""

    enabled: dict[str, bool]
    weights: dict[str, float]


def load_rule_config(path: Path) -> RuleConfig:
    """Load and validate a rules YAML file."""
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
