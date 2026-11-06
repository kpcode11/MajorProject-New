"""Tests for model scoring orchestration (Phase 5, P5-04)."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.config import load_rule_config
from app.schemas import (
    AssessRequest,
    BehaviourPayload,
    EnvSignals,
    KeyBehaviour,
    MouseBehaviour,
)
from app.scoring import (
    EXPECTED_KEYBOARD_FEATURE_NAMES,
    EXPECTED_MOUSE_FEATURE_NAMES,
    ModelMetadataError,
    ModelScorer,
    ScoreResult,
    apply_calibration,
    extract_keyboard_feature_dict,
    extract_mouse_feature_windows,
    fuse_modality_scores,
    load_fusion_metadata,
    load_modality_model,
    load_scorer,
    top_k_contributing_features,
    validate_modality_metadata,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"
RULES_YAML = BACKEND_ROOT / "config" / "rules.yaml"

# Real human trajectory snippet from DELBOT-Mouse (circleHide_1663314082171)
HUMAN_MOUSE_POINTS: list[list[float]] = [
    [756.0, 273.0, 191.0],
    [744.0, 273.0, 199.3],
    [711.0, 280.0, 220.7],
    [687.0, 291.0, 241.5],
    [676.0, 301.0, 256.5],
    [667.0, 315.0, 271.9],
    [657.0, 334.0, 293.8],
    [653.0, 347.0, 309.2],
    [652.0, 359.0, 323.9],
    [653.0, 370.0, 337.8],
    [657.0, 383.0, 360.3],
    [661.0, 391.0, 374.8],
    [670.0, 400.0, 389.2],
    [681.0, 405.0, 404.4],
    [701.0, 411.0, 426.4],
    [715.0, 413.0, 441.1],
    [733.0, 411.0, 455.7],
    [750.0, 405.0, 470.7],
    [777.0, 391.0, 492.8],
    [786.0, 384.0, 507.1],
    [793.0, 379.0, 522.2],
    [802.0, 367.0, 544.1],
    [807.0, 354.0, 558.4],
    [812.0, 342.0, 574.2],
    [813.0, 332.0, 588.7],
    [815.0, 315.0, 610.5],
    [814.0, 306.0, 625.0],
    [813.0, 299.0, 640.0],
    [810.0, 294.0, 654.7],
    [808.0, 289.0, 676.8],
    [805.0, 285.0, 691.4],
    [801.0, 283.0, 706.3],
    [799.0, 281.0, 720.9],
    [793.0, 277.0, 743.4],
    [787.0, 273.0, 757.8],
    [783.0, 271.0, 772.6],
    [778.0, 269.0, 787.0],
    [769.0, 267.0, 809.8],
    [767.0, 267.0, 823.8],
]


def _make_bot_mouse_points() -> list[list[float]]:
    """Straight-line constant-interval (16 ms) bot mouse trajectory."""
    pts: list[list[float]] = []
    t = 0.0
    for step in range(1, 46):
        u = step / 45.0
        pts.append([round(120.0 + u * 660.0, 2), round(150.0 + u * 370.0, 2), t])
        t += 16.0
    return pts


def _make_human_key_events() -> list[list[object]]:
    """Natural variable-rhythm human typing with key rollover and backspace."""
    rng = np.random.default_rng(7)
    events: list[list[object]] = []
    t = 100.0
    for i in range(30):
        dwell = float(rng.lognormal(4.55, 0.32))
        key_cls = "backspace" if i % 9 == 4 else "letter"
        events.append([key_cls, round(t, 1), round(t + dwell, 1)])
        flight = -15.0 if i % 5 == 0 else float(rng.lognormal(4.6, 0.55))
        t = max(t + 5.0, t + dwell + flight)
    return events


def _make_bot_key_events() -> list[list[object]]:
    """Constant-interval K1 bot typing (90 ms dwell, 120 ms flight)."""
    return [["letter", i * 210.0, i * 210.0 + 90.0] for i in range(30)]


def _clean_desktop_env() -> EnvSignals:
    return EnvSignals(
        ua_family="Chrome",
        ua_os="Windows",
        platform="Win32",
        webdriver=False,
        plugins_count=5,
        viewport_w=1440,
        viewport_h=900,
        outer_w=1440,
        outer_h=960,
        screen_w_bucket=1920,
        screen_h_bucket=1080,
        webgl_renderer_class="hardware",
        native_fn_integrity_ok=True,
    )


@pytest.fixture(scope="module")
def scorer() -> ModelScorer:
    """Module-scoped ModelScorer loaded once from backend/models."""
    rule_cfg = load_rule_config(RULES_YAML)
    return load_scorer(MODELS_DIR, rule_config=rule_cfg)


# ---------------------------------------------------------------------------
# 1. Startup loading and metadata validation
# ---------------------------------------------------------------------------


class TestModelLoadingAndMetadataValidation:
    def test_load_scorer_succeeds_and_populates_versions(self, scorer: ModelScorer) -> None:
        versions = scorer.model_versions
        assert versions.mouse == "lightgbm-v1"
        assert versions.keyboard == "logistic_regression-v1"
        assert versions.touch is None
        assert versions.fusion == "v1"
        assert scorer.mouse_model is not None
        assert len(scorer.mouse_model.feature_order) == 120
        assert scorer.keyboard_model is not None
        assert len(scorer.keyboard_model.feature_order) == 31

    def test_validate_modality_metadata_rejects_missing_version(self) -> None:
        with pytest.raises(ModelMetadataError, match="version"):
            validate_modality_metadata("mouse", {"feature_order": ["a", "b"]})

    def test_validate_modality_metadata_rejects_empty_or_duplicate_features(self) -> None:
        with pytest.raises(ModelMetadataError, match="feature_order"):
            validate_modality_metadata("mouse", {"version": "v1", "feature_order": []})
        with pytest.raises(ModelMetadataError, match="duplicate"):
            validate_modality_metadata(
                "mouse", {"version": "v1", "feature_order": ["speed_mean_mean", "speed_mean_mean"]}
            )

    def test_validate_modality_metadata_rejects_unknown_features(self) -> None:
        with pytest.raises(ModelMetadataError, match="unknown features"):
            validate_modality_metadata(
                "mouse",
                {"version": "v1", "feature_order": ["non_existent_feature"]},
                expected_features=EXPECTED_MOUSE_FEATURE_NAMES,
            )

    def test_validate_modality_metadata_rejects_reordered_keyboard_features(self) -> None:
        reversed_kb = list(reversed(EXPECTED_KEYBOARD_FEATURE_NAMES))
        with pytest.raises(ModelMetadataError, match="KEYBOARD_FEATURE_NAMES"):
            validate_modality_metadata(
                "keyboard",
                {"version": "v1", "feature_order": reversed_kb},
                expected_features=EXPECTED_KEYBOARD_FEATURE_NAMES,
            )

    def test_load_modality_model_rejects_onnx_dimension_mismatch(self, tmp_path: Path) -> None:
        mod_dir = tmp_path / "mouse-bad"
        mod_dir.mkdir()
        shutil.copy(MODELS_DIR / "mouse-v1" / "model.onnx", mod_dir / "model.onnx")
        bad_meta = {
            "version": "v1",
            "feature_order": list(EXPECTED_MOUSE_FEATURE_NAMES[:10]),
        }
        (mod_dir / "metadata.json").write_text(json.dumps(bad_meta), encoding="utf-8")
        with pytest.raises(ModelMetadataError, match="ONNX input dimension"):
            load_modality_model(mod_dir, "mouse", expected_features=EXPECTED_MOUSE_FEATURE_NAMES)

    def test_load_fusion_metadata_rejects_unknown_method(self) -> None:
        with pytest.raises(ModelMetadataError, match="fusion method"):
            load_fusion_metadata(MODELS_DIR / "fusion-v1", default_method="invalid_method")


# ---------------------------------------------------------------------------
# 2. Feature extraction delegation (botguard_ml.features)
# ---------------------------------------------------------------------------


class TestFeatureExtractionDelegation:
    def test_mouse_feature_extraction_matches_120_schema(self) -> None:
        mouse = MouseBehaviour(
            points=HUMAN_MOUSE_POINTS,
            clicks=[[767.0, 267.0, 840.0, 920.0]],
        )
        windows = extract_mouse_feature_windows(mouse, _clean_desktop_env())
        assert len(windows) == 1
        feat_dict = windows[0]
        assert set(feat_dict.keys()) == set(EXPECTED_MOUSE_FEATURE_NAMES)
        assert feat_dict["n_segments"] >= 1.0
        assert math.isfinite(feat_dict["speed_mean_mean"])
        assert math.isfinite(feat_dict["bbox_area_norm_mean"])

    def test_mouse_below_minimum_points_returns_empty(self) -> None:
        short_mouse = MouseBehaviour(points=[[10.0, 20.0, 0.0], [15.0, 25.0, 16.0]])
        assert extract_mouse_feature_windows(short_mouse) == []

    def test_keyboard_feature_extraction_matches_31_schema_and_maps_backspace(self) -> None:
        keys = KeyBehaviour(events=_make_human_key_events(), paste_events=1)
        feats = extract_keyboard_feature_dict(keys)
        assert feats is not None
        assert tuple(feats.keys()) == EXPECTED_KEYBOARD_FEATURE_NAMES
        assert feats["n_keys"] == 30.0
        assert feats["backspace_ratio"] > 0.0
        assert feats["rollover_ratio"] > 0.0
        assert feats["paste_events"] == 1.0


# ---------------------------------------------------------------------------
# 3. Calibration, top-3 attribution, and multimodal score fusion
# ---------------------------------------------------------------------------


class TestCalibrationAttributionAndFusion:
    def test_apply_calibration_isotonic_and_platt(self) -> None:
        iso_cfg = {
            "method": "isotonic",
            "x_thresholds": [0.0, 0.5, 1.0],
            "y_thresholds": [0.0, 0.2, 1.0],
        }
        assert apply_calibration(0.25, iso_cfg) == pytest.approx(0.1)
        platt_cfg = {"method": "platt", "coef": 4.0, "intercept": -2.0}
        assert apply_calibration(0.5, platt_cfg) == pytest.approx(0.5)
        assert apply_calibration(0.9, platt_cfg) > 0.8

    @pytest.mark.parametrize(
        ("m_score", "k_score", "t_score", "method", "expected"),
        [
            (None, None, None, "average", None),
            (0.20, None, None, "average", 0.20),
            (None, 0.15, None, "average", 0.15),
            (None, None, 0.10, "noisy_or", 0.10),
            (0.20, 0.40, None, "average", 0.30),
            (0.20, 0.50, None, "noisy_or", 0.60),
            (0.20, 0.80, None, "mouse_only", 0.20),
            (0.20, 0.80, None, "keyboard_only", 0.80),
        ],
    )
    def test_fuse_modality_scores_missing_modality_safe(
        self,
        m_score: float | None,
        k_score: float | None,
        t_score: float | None,
        method: str,
        expected: float | None,
    ) -> None:
        fused = fuse_modality_scores(m_score, k_score, t_score, method=method)
        if expected is None:
            assert fused is None
        else:
            assert fused == pytest.approx(expected)

    def test_fuse_modality_scores_stacker(self) -> None:
        coeffs = {"mouse_weight": 5.0, "keyboard_weight": 5.0, "intercept": -5.0}
        low = fuse_modality_scores(0.05, 0.05, method="stacker", stacker_coefficients=coeffs)
        high = fuse_modality_scores(0.95, 0.95, method="stacker", stacker_coefficients=coeffs)
        assert low is not None and low < 0.10
        assert high is not None and high > 0.90

    def test_top_k_contributing_features_returns_prefixed_names(self, scorer: ModelScorer) -> None:
        assert scorer.mouse_model is not None
        sample_feats = dict(scorer.mouse_model.imputer_medians)
        sample_feats["straightness_mean"] = 1.0
        sample_feats["window_dt_cv"] = 0.001
        top3 = top_k_contributing_features(sample_feats, scorer.mouse_model, k=3)
        assert len(top3) == 3
        assert all(name.startswith("mouse:") for name in top3)


# ---------------------------------------------------------------------------
# 4. End-to-end session scoring (human vs bot vs missing-modality vs fail-safe)
# ---------------------------------------------------------------------------


class TestEndToEndSessionScoring:
    def test_clean_human_session_scores_low_band(self, scorer: ModelScorer) -> None:
        env = _clean_desktop_env()
        behaviour = BehaviourPayload(
            mouse=MouseBehaviour(points=HUMAN_MOUSE_POINTS),
            keys=KeyBehaviour(events=_make_human_key_events()),
            device_class="desktop",
        )
        req = AssessRequest(nonce="test-nonce-1234", action="login", env=env, behaviour=behaviour)
        res: ScoreResult = scorer.score_request(req)

        assert res.band == "low"
        assert res.score < 0.30
        assert res.rule_score == 0.0
        assert res.mouse_score is not None and res.mouse_score < 0.30
        assert res.keyboard_score is not None and res.keyboard_score < 0.10
        assert res.degraded is False
        assert len(res.top_features["mouse"]) == 3
        assert len(res.top_features["keyboard"]) == 3
        assert len(res.reasons) == 6

    def test_straight_line_and_constant_interval_bot_scores_high_band(
        self, scorer: ModelScorer
    ) -> None:
        env = _clean_desktop_env()
        behaviour = BehaviourPayload(
            mouse=MouseBehaviour(points=_make_bot_mouse_points()),
            keys=KeyBehaviour(events=_make_bot_key_events()),
            device_class="desktop",
        )
        res = scorer.score(env, behaviour)

        assert res.band == "high"
        assert res.score >= 0.70
        assert res.mouse_score is not None and res.mouse_score > 0.80
        assert res.keyboard_score is not None and res.keyboard_score > 0.80
        assert res.degraded is False
        assert "mouse" in res.top_features
        assert "keyboard" in res.top_features

    def test_keyboard_only_human_is_not_penalized_for_missing_mouse(
        self, scorer: ModelScorer
    ) -> None:
        env = _clean_desktop_env()
        behaviour = BehaviourPayload(
            mouse=None,
            keys=KeyBehaviour(events=_make_human_key_events()),
            device_class="desktop",
        )
        res = scorer.score(env, behaviour)

        assert res.mouse_score is None
        assert res.keyboard_score is not None and res.keyboard_score < 0.10
        assert res.model_score == pytest.approx(res.keyboard_score)
        assert res.band == "low"
        assert "mouse" not in res.top_features
        assert len(res.top_features["keyboard"]) == 3

    def test_headless_webdriver_rule_combines_with_model_score(self, scorer: ModelScorer) -> None:
        headless_env = EnvSignals(
            ua_family="Chrome",
            ua_os="Windows",
            platform="Linux x86_64",
            webdriver=True,
            plugins_count=0,
            webgl_renderer_class="swiftshader",
        )
        behaviour = BehaviourPayload(
            keys=KeyBehaviour(events=_make_human_key_events()),
        )
        res = scorer.score(headless_env, behaviour)

        assert "R02_WEBDRIVER" in res.fired_rules
        assert "R03_UA_PLATFORM_MISMATCH" in res.fired_rules
        assert res.rule_score > 0.70
        assert res.score >= res.rule_score
        assert res.band == "high"

    def test_hard_rule_bypasses_model_inference(self, scorer: ModelScorer) -> None:
        res = scorer.score(
            _clean_desktop_env(),
            BehaviourPayload(mouse=MouseBehaviour(points=HUMAN_MOUSE_POINTS)),
            rate_limit_exceeded=True,
        )
        assert res.score == 1.0
        assert res.band == "high"
        assert res.model_score is None
        assert "R13_RATE_LIMIT" in res.fired_rules

    def test_missing_model_falls_back_to_rules_only_with_degraded_flag(self) -> None:
        degraded_scorer = ModelScorer(
            mouse_model=None,
            keyboard_model=None,
            rule_config=load_rule_config(RULES_YAML),
        )
        env = EnvSignals(webdriver=True)
        behaviour = BehaviourPayload(mouse=MouseBehaviour(points=HUMAN_MOUSE_POINTS))
        res = degraded_scorer.score(env, behaviour)

        assert res.degraded is True
        assert res.model_score is None
        assert res.score == pytest.approx(res.rule_score)
        assert res.band == "medium"
        serialized: dict[str, Any] = res.to_dict()
        assert serialized["degraded"] is True
        assert serialized["band"] == "medium"
