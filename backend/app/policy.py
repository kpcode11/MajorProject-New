"""Risk-policy decisions and step-up selection (P5-05).

The policy maps a numeric risk score (0.0 = definitely human, 1.0 = definitely
bot) plus an action class to one of three decisions:

    ``allow``      — issue a signed token and let the request proceed.
    ``challenge``  — show a step-up challenge (press-and-hold or keyboard).
    ``deny``       — reject the request outright.

The exact score is **never** returned to untrusted callers.  A coarse band
(``low``, ``medium``, ``high``) is all that is exposed in the assess response.

Configuration lives in ``backend/config/policy.yaml`` (Appendix C.1).

Fail-safe behaviour when infrastructure is degraded:
- ``redis_down``    → deny actions with class ``high``; allow ``low``/``medium``.
- ``model_error``   → use rules-only score with ``degraded=True``.
- ``db_down``       → continue scoring; buffer log writes.

Usage::

    from app.policy import load_policy, PolicyEngine

    engine = load_policy(Path("backend/config/policy.yaml"))
    decision = engine.decide(score=0.42, action="otp_request")
    # Decision(verdict="challenge", band="medium")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Verdict = Literal["allow", "challenge", "deny"]
Band = Literal["low", "medium", "high"]
FailSafeMode = Literal["deny_high_allow_low", "rules_only", "continue_and_buffer"]


@dataclass(frozen=True)
class Decision:
    """Result of a policy evaluation."""

    verdict: Verdict
    band: Band
    degraded: bool = False


# ---------------------------------------------------------------------------
# Action-class thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionClassThresholds:
    """Score thresholds for one action sensitivity class.

    Invariant: ``0 ≤ allow_below ≤ deny_at_or_above ≤ 1``.
    """

    allow_below: float
    deny_at_or_above: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.allow_below <= self.deny_at_or_above <= 1.0):
            raise ValueError(
                f"Thresholds must satisfy 0 ≤ allow_below ({self.allow_below}) "
                f"≤ deny_at_or_above ({self.deny_at_or_above}) ≤ 1"
            )


# ---------------------------------------------------------------------------
# PolicyConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyConfig:
    """Parsed and validated policy configuration."""

    # Sensitivity-class definitions.
    action_classes: dict[str, ActionClassThresholds]
    # Action name → sensitivity class name.
    actions: dict[str, str]
    # Fail-safe modes.
    fail_safe_redis_down: FailSafeMode
    fail_safe_model_error: FailSafeMode
    fail_safe_db_down: FailSafeMode
    # Band cutoffs (score < low_cutoff → low; < medium_cutoff → medium; else high).
    band_low_cutoff: float
    band_medium_cutoff: float


_VALID_FAIL_SAFE: frozenset[str] = frozenset(
    {"deny_high_allow_low", "rules_only", "continue_and_buffer"}
)


def load_policy(path: Path) -> PolicyEngine:
    """Load a ``policy.yaml`` file and return a :class:`PolicyEngine`.

    Args:
        path: Path to the YAML config file.

    Returns:
        A configured :class:`PolicyEngine`.

    Raises:
        ValueError: If the file is missing required keys or contains invalid values.
        OSError: If the file cannot be read.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # -- action_classes -------------------------------------------------------
    ac_raw = raw.get("action_classes")
    if not isinstance(ac_raw, dict):
        raise ValueError("policy.yaml must define an 'action_classes' mapping")

    action_classes: dict[str, ActionClassThresholds] = {}
    for cls_name, cfg in ac_raw.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"action_classes.{cls_name} must be a mapping")
        try:
            action_classes[cls_name] = ActionClassThresholds(
                allow_below=float(cfg["allow_below"]),
                deny_at_or_above=float(cfg["deny_at_or_above"]),
            )
        except KeyError as e:
            raise ValueError(f"action_classes.{cls_name} missing key: {e}") from e

    # -- actions ---------------------------------------------------------------
    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, dict):
        raise ValueError("policy.yaml must define an 'actions' mapping")
    for act, cls in actions_raw.items():
        if cls not in action_classes:
            raise ValueError(
                f"action '{act}' references unknown class '{cls}'. "
                f"Known classes: {sorted(action_classes)}"
            )
    actions: dict[str, str] = dict(actions_raw)

    # -- fail_safe -------------------------------------------------------------
    fs_raw = raw.get("fail_safe", {})
    if not isinstance(fs_raw, dict):
        raise ValueError("policy.yaml 'fail_safe' must be a mapping")

    def _fs(key: str, default: str) -> FailSafeMode:
        val = str(fs_raw.get(key, default))
        if val not in _VALID_FAIL_SAFE:
            raise ValueError(
                f"fail_safe.{key} must be one of {sorted(_VALID_FAIL_SAFE)}, got {val!r}"
            )
        return val  # type: ignore[return-value]

    fail_safe_redis = _fs("redis_down", "deny_high_allow_low")
    fail_safe_model = _fs("model_error", "rules_only")
    fail_safe_db = _fs("db_down", "continue_and_buffer")

    # -- band_cutoffs ----------------------------------------------------------
    bc_raw = raw.get("band_cutoffs", {})
    if not isinstance(bc_raw, dict):
        raise ValueError("policy.yaml 'band_cutoffs' must be a mapping")
    band_low = float(bc_raw.get("low", 0.30))
    band_medium = float(bc_raw.get("medium", 0.70))
    if not (0.0 <= band_low < band_medium <= 1.0):
        raise ValueError(
            f"band_cutoffs must satisfy 0 ≤ low ({band_low}) < medium ({band_medium}) ≤ 1"
        )

    config = PolicyConfig(
        action_classes=action_classes,
        actions=actions,
        fail_safe_redis_down=fail_safe_redis,
        fail_safe_model_error=fail_safe_model,
        fail_safe_db_down=fail_safe_db,
        band_low_cutoff=band_low,
        band_medium_cutoff=band_medium,
    )
    return PolicyEngine(config)


# ---------------------------------------------------------------------------
# PolicyEngine
# ---------------------------------------------------------------------------


class PolicyEngine:
    """Applies the loaded policy to produce a :class:`Decision`.

    Args:
        config: A :class:`PolicyConfig` instance loaded by :func:`load_policy`.
    """

    def __init__(self, config: PolicyConfig) -> None:
        self._cfg = config

    # -- Helpers -------------------------------------------------------------

    def score_to_band(self, score: float) -> Band:
        """Map a score in [0, 1] to a coarse risk band.

        Args:
            score: Numeric risk score.

        Returns:
            ``"low"``, ``"medium"``, or ``"high"``.
        """
        if score < self._cfg.band_low_cutoff:
            return "low"
        if score < self._cfg.band_medium_cutoff:
            return "medium"
        return "high"

    def _thresholds_for(self, action: str) -> ActionClassThresholds:
        """Resolve thresholds for *action*, falling back to 'medium' class."""
        cls_name = self._cfg.actions.get(action)
        if cls_name is None:
            # Unknown action: fall back to the most restrictive known class.
            cls_name = self._cfg.actions.get("_default", "high")
            if cls_name not in self._cfg.action_classes:
                # If there's no 'high' class either, pick the strictest one.
                cls_name = min(
                    self._cfg.action_classes,
                    key=lambda k: self._cfg.action_classes[k].allow_below,
                )
        return self._cfg.action_classes[cls_name]

    # -- Core decision -------------------------------------------------------

    def decide(
        self,
        score: float,
        action: str,
        *,
        degraded: bool = False,
    ) -> Decision:
        """Apply the policy thresholds to produce a verdict.

        Args:
            score: Risk score in [0.0, 1.0] (0 = human, 1 = bot).
            action: Action identifier, e.g. ``"otp_request"``.
            degraded: Whether scoring was in degraded mode (e.g. model error).

        Returns:
            A :class:`Decision` with ``verdict``, ``band``, and ``degraded``.
        """
        band = self.score_to_band(score)
        thresholds = self._thresholds_for(action)

        if score < thresholds.allow_below:
            verdict: Verdict = "allow"
        elif score >= thresholds.deny_at_or_above:
            verdict = "deny"
        else:
            verdict = "challenge"

        return Decision(verdict=verdict, band=band, degraded=degraded)

    # -- Fail-safe decisions -------------------------------------------------

    def decide_redis_down(self, action: str) -> Decision:
        """Fallback decision when the Store/Redis is unavailable.

        Policy: ``deny_high_allow_low`` — deny high-sensitivity actions,
        allow low-sensitivity ones, challenge everything else.
        Returned with ``degraded=True``.
        """
        cls_name = self._cfg.actions.get(action, "high")
        if cls_name == "low":
            return Decision(verdict="allow", band="low", degraded=True)
        if cls_name == "high":
            return Decision(verdict="deny", band="high", degraded=True)
        return Decision(verdict="challenge", band="medium", degraded=True)

    def decide_model_error(
        self,
        rule_score: float,
        action: str,
    ) -> Decision:
        """Fallback decision when the ML model is unavailable.

        Policy: ``rules_only`` — use the rule score only (no model score).
        Returned with ``degraded=True``.
        """
        base = self.decide(rule_score, action, degraded=True)
        return Decision(verdict=base.verdict, band=base.band, degraded=True)

    # -- Configuration accessors ---------------------------------------------

    @property
    def config(self) -> PolicyConfig:
        """The underlying :class:`PolicyConfig`."""
        return self._cfg
