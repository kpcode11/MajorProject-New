"""Tests for risk-policy loading and decision engine (P5-05)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.policy import Decision, PolicyEngine, load_policy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_policy(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _default_engine(tmp_path: Path) -> PolicyEngine:
    """Load the real backend/config/policy.yaml."""
    root = Path(__file__).resolve().parents[1]
    return load_policy(root / "config" / "policy.yaml")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


class TestLoadPolicy:
    def test_loads_real_policy_yaml(self, tmp_path: Path) -> None:
        engine = _default_engine(tmp_path)
        assert engine is not None

    def test_missing_action_classes_raises(self, tmp_path: Path) -> None:
        p = _write_policy(tmp_path, "actions:\n  login: medium\n")
        with pytest.raises(ValueError, match="action_classes"):
            load_policy(p)

    def test_unknown_action_class_raises(self, tmp_path: Path) -> None:
        p = _write_policy(
            tmp_path,
            """\
            action_classes:
              low: {allow_below: 0.5, deny_at_or_above: 0.9}
            actions:
              login: high
            """,
        )
        with pytest.raises(ValueError, match="unknown class"):
            load_policy(p)

    def test_invalid_threshold_order_raises(self, tmp_path: Path) -> None:
        p = _write_policy(
            tmp_path,
            """\
            action_classes:
              low: {allow_below: 0.9, deny_at_or_above: 0.3}
            actions:
              login: low
            """,
        )
        with pytest.raises(ValueError):
            load_policy(p)

    def test_invalid_fail_safe_value_raises(self, tmp_path: Path) -> None:
        p = _write_policy(
            tmp_path,
            """\
            action_classes:
              low: {allow_below: 0.5, deny_at_or_above: 0.9}
            actions:
              login: low
            fail_safe:
              redis_down: magic_answer
            """,
        )
        with pytest.raises(ValueError, match="fail_safe"):
            load_policy(p)

    def test_invalid_band_cutoffs_raises(self, tmp_path: Path) -> None:
        p = _write_policy(
            tmp_path,
            """\
            action_classes:
              low: {allow_below: 0.5, deny_at_or_above: 0.9}
            actions:
              login: low
            band_cutoffs:
              low: 0.8
              medium: 0.3
            """,
        )
        with pytest.raises(ValueError, match="band_cutoffs"):
            load_policy(p)


# ---------------------------------------------------------------------------
# score_to_band
# ---------------------------------------------------------------------------


class TestScoreToBand:
    def setup_method(self) -> None:
        self.engine = _default_engine(Path("."))

    def test_below_low_cutoff_is_low(self) -> None:
        assert self.engine.score_to_band(0.0) == "low"
        assert self.engine.score_to_band(0.29) == "low"

    def test_at_low_cutoff_is_medium(self) -> None:
        assert self.engine.score_to_band(0.30) == "medium"

    def test_below_medium_cutoff_is_medium(self) -> None:
        assert self.engine.score_to_band(0.69) == "medium"

    def test_at_medium_cutoff_is_high(self) -> None:
        assert self.engine.score_to_band(0.70) == "high"

    def test_max_score_is_high(self) -> None:
        assert self.engine.score_to_band(1.0) == "high"


# ---------------------------------------------------------------------------
# decide — action classes
# ---------------------------------------------------------------------------


class TestDecideActionClasses:
    """Real policy.yaml has low/medium/high action classes."""

    def setup_method(self) -> None:
        self.engine = _default_engine(Path("."))

    # -- low class (page_view): allow_below=0.50, deny_at_or_above=0.90
    def test_low_class_allow(self) -> None:
        d = self.engine.decide(0.10, "page_view")
        assert d.verdict == "allow"
        assert d.band == "low"

    def test_low_class_challenge(self) -> None:
        d = self.engine.decide(0.60, "page_view")
        assert d.verdict == "challenge"

    def test_low_class_deny(self) -> None:
        d = self.engine.decide(0.95, "page_view")
        assert d.verdict == "deny"
        assert d.band == "high"

    # -- medium class (login): allow_below=0.30, deny_at_or_above=0.80
    def test_medium_class_allow(self) -> None:
        d = self.engine.decide(0.20, "login")
        assert d.verdict == "allow"

    def test_medium_class_challenge(self) -> None:
        d = self.engine.decide(0.50, "login")
        assert d.verdict == "challenge"

    def test_medium_class_deny(self) -> None:
        d = self.engine.decide(0.85, "login")
        assert d.verdict == "deny"

    # -- high class (otp_request): allow_below=0.15, deny_at_or_above=0.70
    def test_high_class_allow(self) -> None:
        d = self.engine.decide(0.05, "otp_request")
        assert d.verdict == "allow"

    def test_high_class_challenge(self) -> None:
        d = self.engine.decide(0.40, "otp_request")
        assert d.verdict == "challenge"

    def test_high_class_deny(self) -> None:
        d = self.engine.decide(0.75, "otp_request")
        assert d.verdict == "deny"

    # -- Unknown action falls back to most restrictive
    def test_unknown_action_is_conservative(self) -> None:
        d = self.engine.decide(0.50, "unknown_action_xyz")
        # A score of 0.50 should challenge or deny for the most restrictive class.
        assert d.verdict in ("challenge", "deny")

    # -- degraded flag is preserved
    def test_degraded_flag_preserved(self) -> None:
        d = self.engine.decide(0.05, "otp_request", degraded=True)
        assert d.degraded is True

    def test_non_degraded_by_default(self) -> None:
        d = self.engine.decide(0.05, "otp_request")
        assert d.degraded is False


# ---------------------------------------------------------------------------
# Threshold boundaries (exact edge values)
# ---------------------------------------------------------------------------


class TestThresholdBoundaries:
    def setup_method(self) -> None:
        self.engine = _default_engine(Path("."))

    def test_allow_below_is_exclusive_upper(self) -> None:
        """Score exactly at allow_below should NOT be allowed (goes to challenge)."""
        # otp_request allow_below = 0.15
        d = self.engine.decide(0.15, "otp_request")
        assert d.verdict in ("challenge", "deny")

    def test_just_below_allow_is_allowed(self) -> None:
        d = self.engine.decide(0.14, "otp_request")
        assert d.verdict == "allow"

    def test_deny_at_or_above_is_inclusive(self) -> None:
        """Score exactly at deny_at_or_above should be denied."""
        # otp_request deny_at_or_above = 0.70
        d = self.engine.decide(0.70, "otp_request")
        assert d.verdict == "deny"

    def test_just_below_deny_is_challenge(self) -> None:
        d = self.engine.decide(0.69, "otp_request")
        assert d.verdict == "challenge"


# ---------------------------------------------------------------------------
# Fail-safe decisions
# ---------------------------------------------------------------------------


class TestFailSafeDecisions:
    def setup_method(self) -> None:
        self.engine = _default_engine(Path("."))

    def test_redis_down_low_action_allows(self) -> None:
        d = self.engine.decide_redis_down("page_view")
        assert d.verdict == "allow"
        assert d.degraded is True

    def test_redis_down_high_action_denies(self) -> None:
        d = self.engine.decide_redis_down("otp_request")
        assert d.verdict == "deny"
        assert d.degraded is True

    def test_redis_down_medium_action_challenges(self) -> None:
        d = self.engine.decide_redis_down("login")
        assert d.verdict == "challenge"
        assert d.degraded is True

    def test_model_error_uses_rule_score(self) -> None:
        # Low rule score -> allow even in degraded mode.
        d = self.engine.decide_model_error(rule_score=0.05, action="otp_request")
        assert d.verdict == "allow"
        assert d.degraded is True

    def test_model_error_high_rule_score_denies(self) -> None:
        d = self.engine.decide_model_error(rule_score=0.85, action="otp_request")
        assert d.verdict == "deny"
        assert d.degraded is True


# ---------------------------------------------------------------------------
# Decision is a frozen dataclass
# ---------------------------------------------------------------------------


class TestDecisionDataclass:
    def test_decision_is_immutable(self) -> None:
        d = Decision(verdict="allow", band="low")
        with pytest.raises((AttributeError, TypeError)):
            d.verdict = "deny"  # type: ignore[misc]

    def test_decision_equality(self) -> None:
        a = Decision(verdict="allow", band="low", degraded=False)
        b = Decision(verdict="allow", band="low", degraded=False)
        assert a == b
