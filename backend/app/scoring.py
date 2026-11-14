"""Model scoring orchestration (Phase 5, P5-04).

Responsibilities:
1. Load ONNX sessions once at startup (mouse, keyboard, optional touch) and
   validate their ``metadata.json`` files (version, feature order, ONNX input
   dimension, and calibration parameters).
2. Extract behavioural features by importing the **same** feature functions
   from ``botguard_ml.features`` (zero duplicated feature math).
3. Run ONNX inference with median imputation, apply stored probability
   calibration (isotonic or Platt scaling), fuse active modalities according to
   the ``fusion`` metadata (never penalizing missing modalities), and combine
   with the deterministic environment rule score (``max(model_score, rule_score)``).
4. Provide per-request explainability: fired rule reasons plus the top-3
   contributing features per active modality using pre-computed SHAP/coefficient
   importance weighted by normalized deviation from training medians (with
   fallback to global importance rank, since ONNX Runtime tree/linear classifiers
   emit probabilities rather than per-tree TreeSHAP tensors at serving time).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]
from botguard_ml.features.keyboard import (
    KEYBOARD_FEATURE_NAMES,
    keyboard_features,
    validate_keyboard_features,
)
from botguard_ml.features.mouse import (
    AGGREGATE_STATS,
    SEGMENT_FEATURE_NAMES,
    extract_window_features,
)
from botguard_ml.features.windowing import window_events

from app.config import RuleConfig
from app.policy import Band
from app.rules import RuleScore, evaluate_rule_score
from app.schemas import (
    AssessRequest,
    BehaviourPayload,
    EnvSignals,
    KeyBehaviour,
    ModelVersions,
    MouseBehaviour,
)

# ---------------------------------------------------------------------------
# Constants & Canonical Feature Schemas
# ---------------------------------------------------------------------------

WINDOW_TIMING_FEATURE_NAMES: tuple[str, ...] = (
    "window_duration_ms",
    "window_n_points",
    "window_dt_mean",
    "window_dt_std",
    "window_dt_cv",
    "window_dt_mode_fraction",
    "window_pause_count",
    "window_pause_total_ms",
    "n_segments",
)

EXPECTED_MOUSE_FEATURE_NAMES: tuple[str, ...] = (
    *(f"{seg_feat}_{stat}" for seg_feat in SEGMENT_FEATURE_NAMES for stat in AGGREGATE_STATS),
    *WINDOW_TIMING_FEATURE_NAMES,
)

EXPECTED_KEYBOARD_FEATURE_NAMES: tuple[str, ...] = tuple(KEYBOARD_FEATURE_NAMES)

MIN_MOUSE_MOVE_POINTS: int = 8
MIN_KEYBOARD_EVENTS: int = 2

EXPLAINABILITY_LIMITATION_NOTE: str = (
    "ONNX Runtime classifiers output class probabilities rather than exact per-tree "
    "TreeSHAP tensors at serving time; top-3 modality features are ranked using "
    "pre-computed global SHAP/coefficient importance weighted by normalized feature "
    "deviation from training medians (falling back to global importance rank)."
)


class ModelMetadataError(ValueError):
    """Raised when an ONNX model or its metadata.json fails startup validation."""


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreResult:
    """Output of the combined rule + multimodal ML scoring pipeline (P5-04).

    Attributes:
        score: Final combined risk score in ``[0.0, 1.0]`` (0 = human, 1 = bot).
        band: Coarse client-safe risk band (``"low"``, ``"medium"``, ``"high"``).
        reasons: Human-readable explanation strings (fired rule reasons plus
            top-3 feature contributors for each active behavioural modality).
        model_versions: Loaded version strings for mouse, keyboard, touch, fusion.
        rule_score: Risk score produced by the deterministic rule layer R01-R13.
        model_score: Fused behavioural model probability, or ``None`` if no
            behavioural modality was present or models were bypassed/degraded.
        mouse_score: Calibrated mouse probability, or ``None`` if absent.
        keyboard_score: Calibrated keyboard probability, or ``None`` if absent.
        touch_score: Calibrated touch probability, or ``None`` if absent.
        fired_rules: List of rule IDs (e.g. ``["R02_WEBDRIVER"]``) that fired.
        top_features: Mapping of modality name to its top-3 contributing features.
        degraded: ``True`` if an unexpected model error forced rules-only fallback.
        explainability_note: Note describing the serving-time feature attribution.
    """

    score: float
    band: Band
    reasons: list[str]
    model_versions: ModelVersions
    rule_score: float = 0.0
    model_score: float | None = None
    mouse_score: float | None = None
    keyboard_score: float | None = None
    touch_score: float | None = None
    fired_rules: list[str] = field(default_factory=list)
    top_features: dict[str, list[str]] = field(default_factory=dict)
    derived_features: dict[str, float] = field(default_factory=dict)
    degraded: bool = False
    explainability_note: str = EXPLAINABILITY_LIMITATION_NOTE

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full score result for internal logging and admin inspection."""
        return {
            "score": self.score,
            "band": self.band,
            "reasons": list(self.reasons),
            "model_versions": self.model_versions.model_dump(),
            "rule_score": self.rule_score,
            "model_score": self.model_score,
            "mouse_score": self.mouse_score,
            "keyboard_score": self.keyboard_score,
            "touch_score": self.touch_score,
            "fired_rules": list(self.fired_rules),
            "top_features": {k: list(v) for k, v in self.top_features.items()},
            "degraded": self.degraded,
            "explainability_note": self.explainability_note,
        }


@dataclass
class LoadedModalityModel:
    """A validated ONNX session and its preprocessing/calibration metadata."""

    modality: str
    version: str
    model_family: str
    feature_order: tuple[str, ...]
    imputer_medians: dict[str, float]
    calibration: dict[str, Any]
    feature_importance: dict[str, float]
    session: ort.InferenceSession
    input_name: str
    prob_output_name: str

    @property
    def version_tag(self) -> str:
        """Formatted version string, e.g. ``'lightgbm-v1'``."""
        return f"{self.model_family}-{self.version}"


@dataclass(frozen=True)
class LoadedFusionMetadata:
    """Validated multimodal score-fusion metadata."""

    version: str
    methods: tuple[str, ...]
    default_method: str
    stacker_coefficients: dict[str, float]
    missing_modality_policy: str


# ---------------------------------------------------------------------------
# Startup Validation & Loading
# ---------------------------------------------------------------------------


def validate_modality_metadata(
    modality: str,
    metadata: dict[str, Any],
    *,
    expected_features: tuple[str, ...] | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Validate version and feature_order in a modality's ``metadata.json``.

    Raises:
        ModelMetadataError: If required fields are missing or invalid.
    """
    if not isinstance(metadata, dict):
        raise ModelMetadataError(f"{modality} metadata must be a JSON object")

    version = metadata.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ModelMetadataError(f"{modality} metadata missing non-empty 'version' string")

    raw_order = metadata.get("feature_order")
    if not isinstance(raw_order, list) or not raw_order:
        raise ModelMetadataError(f"{modality} metadata missing non-empty 'feature_order' list")
    if not all(isinstance(f, str) and f.strip() for f in raw_order):
        raise ModelMetadataError(f"{modality} feature_order must contain only non-empty strings")

    feature_order = tuple(str(f) for f in raw_order)
    if len(set(feature_order)) != len(feature_order):
        raise ModelMetadataError(f"{modality} feature_order contains duplicate feature names")

    if expected_features is not None:
        expected_set = set(expected_features)
        unknown = [f for f in feature_order if f not in expected_set]
        if unknown:
            raise ModelMetadataError(
                f"{modality} feature_order contains unknown features not in "
                f"botguard_ml.features: {unknown[:5]}"
            )
        if modality == "keyboard" and feature_order != expected_features:
            raise ModelMetadataError(
                f"keyboard feature_order does not match KEYBOARD_FEATURE_NAMES: "
                f"got {len(feature_order)} features, expected {len(expected_features)}"
            )

    return version.strip(), feature_order


def load_modality_model(
    model_dir: Path,
    modality: str,
    *,
    expected_features: tuple[str, ...] | None = None,
) -> LoadedModalityModel:
    """Load and validate one ONNX model directory (`model.onnx` + `metadata.json`)."""
    meta_path = model_dir / "metadata.json"
    onnx_path = model_dir / "model.onnx"
    if not meta_path.exists():
        raise ModelMetadataError(f"Missing {modality} metadata file: {meta_path}")
    if not onnx_path.exists():
        raise ModelMetadataError(f"Missing {modality} ONNX file: {onnx_path}")

    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelMetadataError(f"Invalid JSON in {meta_path}: {exc}") from exc

    version, feature_order = validate_modality_metadata(
        modality, metadata, expected_features=expected_features
    )

    try:
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    except Exception as exc:
        raise ModelMetadataError(f"Failed to load ONNX session from {onnx_path}: {exc}") from exc

    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if not inputs or not outputs:
        raise ModelMetadataError(f"ONNX model {onnx_path} has no inputs or outputs")

    input_shape = inputs[0].shape
    if isinstance(input_shape, (list, tuple)) and len(input_shape) >= 2:
        expected_dim = input_shape[1]
        if isinstance(expected_dim, int) and expected_dim != len(feature_order):
            raise ModelMetadataError(
                f"{modality} ONNX input dimension ({expected_dim}) does not match "
                f"feature_order length ({len(feature_order)})"
            )

    raw_medians = metadata.get("imputer_medians") or {}
    imputer_medians = {
        str(k): float(v)
        for k, v in raw_medians.items()
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    }

    raw_importance = metadata.get("feature_importance") or {}
    feature_importance = {
        str(k): abs(float(v))
        for k, v in raw_importance.items()
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    }

    calibration = metadata.get("calibration")
    if not isinstance(calibration, dict):
        calibration = {}

    model_family = str(metadata.get("model", modality)).strip() or modality

    return LoadedModalityModel(
        modality=modality,
        version=version,
        model_family=model_family,
        feature_order=feature_order,
        imputer_medians=imputer_medians,
        calibration=calibration,
        feature_importance=feature_importance,
        session=session,
        input_name=str(inputs[0].name),
        prob_output_name=str(outputs[-1].name),
    )


def load_fusion_metadata(
    fusion_dir: Path,
    *,
    default_method: str = "average",
) -> LoadedFusionMetadata:
    """Load and validate ``fusion-<version>/metadata.json``."""
    meta_path = fusion_dir / "metadata.json"
    if not meta_path.exists():
        raise ModelMetadataError(f"Missing fusion metadata file: {meta_path}")

    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelMetadataError(f"Invalid JSON in {meta_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ModelMetadataError("Fusion metadata must be a JSON object")

    version = raw.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ModelMetadataError("Fusion metadata missing non-empty 'version' string")

    methods_raw = raw.get("methods")
    if not isinstance(methods_raw, list) or not methods_raw:
        raise ModelMetadataError("Fusion metadata missing non-empty 'methods' list")
    methods = tuple(str(m) for m in methods_raw)

    if default_method not in methods:
        raise ModelMetadataError(
            f"Requested fusion method {default_method!r} not in fusion metadata methods {methods}"
        )

    coeffs_raw = raw.get("stacker_coefficients") or {}
    coeffs = {
        str(k): float(v)
        for k, v in coeffs_raw.items()
        if isinstance(v, (int, float)) and math.isfinite(float(v))
    }

    return LoadedFusionMetadata(
        version=version.strip(),
        methods=methods,
        default_method=default_method,
        stacker_coefficients=coeffs,
        missing_modality_policy=str(
            raw.get("missing_modality_policy", "fuse only modalities that are available")
        ),
    )


# ---------------------------------------------------------------------------
# Feature Extraction Helpers (Delegating to botguard_ml.features)
# ---------------------------------------------------------------------------


def mouse_behaviour_to_events(
    mouse: MouseBehaviour,
    env: EnvSignals | None = None,
) -> list[dict[str, Any]]:
    """Convert a ``MouseBehaviour`` schema payload into canonical ML event dicts."""
    screen_w: float | None = None
    screen_h: float | None = None
    if env is not None:
        if env.screen_w_bucket is not None and env.screen_w_bucket > 0:
            screen_w = float(env.screen_w_bucket)
        elif env.viewport_w is not None and env.viewport_w > 0:
            screen_w = float(env.viewport_w)

        if env.screen_h_bucket is not None and env.screen_h_bucket > 0:
            screen_h = float(env.screen_h_bucket)
        elif env.viewport_h is not None and env.viewport_h > 0:
            screen_h = float(env.viewport_h)

    events: list[dict[str, Any]] = []
    for pt in mouse.points:
        if len(pt) >= 3:
            ev: dict[str, Any] = {
                "event": "move",
                "x": float(pt[0]),
                "y": float(pt[1]),
                "t_ms": float(pt[2]),
            }
            if screen_w is not None and screen_h is not None:
                ev["screen_w"] = screen_w
                ev["screen_h"] = screen_h
            events.append(ev)

    for clk in mouse.clicks:
        if len(clk) >= 4:
            x, y, down_ms, up_ms = float(clk[0]), float(clk[1]), float(clk[2]), float(clk[3])
            down_ev: dict[str, Any] = {"event": "down", "x": x, "y": y, "t_ms": down_ms}
            up_ev: dict[str, Any] = {"event": "up", "x": x, "y": y, "t_ms": up_ms}
            if screen_w is not None and screen_h is not None:
                down_ev["screen_w"] = screen_w
                down_ev["screen_h"] = screen_h
                up_ev["screen_w"] = screen_w
                up_ev["screen_h"] = screen_h
            events.append(down_ev)
            events.append(up_ev)

    events.sort(key=lambda item: float(item["t_ms"]))
    return events


def extract_mouse_feature_windows(
    mouse: MouseBehaviour,
    env: EnvSignals | None = None,
    *,
    include_shortcut_features: bool = True,
) -> list[dict[str, float]]:
    """Extract 120-feature mouse window dictionaries using ``botguard_ml.features.mouse``."""
    if len(mouse.points) < MIN_MOUSE_MOVE_POINTS:
        return []
    events = mouse_behaviour_to_events(mouse, env)
    windows = window_events(events, window_s=10.0, hop_s=5.0, min_moves=20)
    if not windows:
        # Trace has >= 8 move points but < 20 move points; score as a single window
        windows = [events]
    return [
        extract_window_features(win, include_shortcut_features=include_shortcut_features)
        for win in windows
    ]


def key_behaviour_to_events(keys: KeyBehaviour) -> list[dict[str, Any]]:
    """Convert a ``KeyBehaviour`` schema payload into canonical ML key-event dicts."""
    events: list[dict[str, Any]] = []
    for item in keys.events:
        if len(item) >= 3:
            raw_cls = str(item[0])
            # Map 'backspace' to 'control' to match Aalto canonical key_class in keyboard_features
            canonical_cls = "control" if raw_cls == "backspace" else raw_cls
            events.append(
                {
                    "key_class": canonical_cls,
                    "down_ms": float(item[1]),  # type: ignore[arg-type]
                    "up_ms": float(item[2]),  # type: ignore[arg-type]
                }
            )
    return events


def extract_keyboard_feature_dict(keys: KeyBehaviour) -> dict[str, float] | None:
    """Extract 31 text-agnostic keyboard features using ``botguard_ml.features.keyboard``."""
    if len(keys.events) < MIN_KEYBOARD_EVENTS:
        return None
    kb_events = key_behaviour_to_events(keys)
    if len(kb_events) < MIN_KEYBOARD_EVENTS:
        return None
    feats = keyboard_features(kb_events)
    feats["paste_events"] = float(keys.paste_events)
    validate_keyboard_features(feats)
    return feats


# ---------------------------------------------------------------------------
# Calibration, Attribution & Fusion Math
# ---------------------------------------------------------------------------


def apply_calibration(raw_prob: float, calibration: dict[str, Any]) -> float:
    """Apply stored probability calibration (isotonic or Platt scaling) to ``raw_prob``."""
    p = float(np.clip(raw_prob, 0.0, 1.0))
    method = str(calibration.get("method", "")).lower()
    if method == "isotonic":
        x_thr = calibration.get("x_thresholds")
        y_thr = calibration.get("y_thresholds")
        if (
            isinstance(x_thr, list)
            and isinstance(y_thr, list)
            and len(x_thr) >= 2
            and len(x_thr) == len(y_thr)
        ):
            p = float(np.interp(p, np.asarray(x_thr, dtype=float), np.asarray(y_thr, dtype=float)))
    elif method == "platt":
        coef = calibration.get("coef")
        intercept = calibration.get("intercept")
        if isinstance(coef, (int, float)) and isinstance(intercept, (int, float)):
            logit = float(coef) * p + float(intercept)
            logit = max(-60.0, min(60.0, logit))
            p = float(1.0 / (1.0 + math.exp(-logit)))
    return float(np.clip(p, 0.0, 1.0))


def top_k_contributing_features(
    feature_dict: dict[str, float],
    model: LoadedModalityModel,
    *,
    k: int = 3,
) -> list[str]:
    """Return the top-k contributing feature names for a scored modality.

    Uses pre-computed SHAP/coefficient importance weighted by normalized feature
    deviation from the training median, falling back to global importance rank.
    """
    scored: list[tuple[float, float, str]] = []
    for idx, feat in enumerate(model.feature_order):
        global_weight = model.feature_importance.get(feat, 1.0 / float(idx + 1))
        val = feature_dict.get(feat, float("nan"))
        median = model.imputer_medians.get(feat, 0.0)
        if math.isfinite(val):
            scale = max(abs(median), 1.0)
            norm_dev = abs(val - median) / scale
        else:
            norm_dev = 0.0
        approx_contrib = global_weight * norm_dev
        scored.append((approx_contrib, global_weight, feat))

    # Sort primarily by per-instance approximate contribution, breaking ties by global importance
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [f"{model.modality}:{item[2]}" for item in scored[:k]]


def fuse_modality_scores(
    mouse_score: float | None,
    keyboard_score: float | None,
    touch_score: float | None = None,
    *,
    method: str = "average",
    stacker_coefficients: dict[str, float] | None = None,
) -> float | None:
    """Fuse available calibrated modality probabilities.

    Missing modalities (``None``) are omitted; absence is never treated as bot evidence.
    """
    available = [score for score in (mouse_score, keyboard_score, touch_score) if score is not None]
    if not available:
        return None

    if method == "mouse_only":
        return mouse_score
    if method == "keyboard_only":
        return keyboard_score
    if len(available) == 1:
        return float(np.clip(available[0], 0.0, 1.0))

    if method == "average":
        return float(np.clip(float(np.mean(available)), 0.0, 1.0))

    if method == "noisy_or":
        prod_complement = 1.0
        for s in available:
            prod_complement *= 1.0 - float(np.clip(s, 0.0, 1.0))
        return float(np.clip(1.0 - prod_complement, 0.0, 1.0))

    if method == "stacker":
        coeffs = stacker_coefficients or {}
        if (
            mouse_score is not None
            and keyboard_score is not None
            and "mouse_weight" in coeffs
            and "keyboard_weight" in coeffs
            and "intercept" in coeffs
        ):
            logit = (
                float(coeffs["mouse_weight"]) * float(mouse_score)
                + float(coeffs["keyboard_weight"]) * float(keyboard_score)
                + float(coeffs["intercept"])
            )
            logit = max(-60.0, min(60.0, logit))
            desktop_fused = float(1.0 / (1.0 + math.exp(-logit)))
            if touch_score is not None:
                return float(np.clip(0.5 * (desktop_fused + float(touch_score)), 0.0, 1.0))
            return float(np.clip(desktop_fused, 0.0, 1.0))
        return float(np.clip(float(np.mean(available)), 0.0, 1.0))

    raise ValueError(f"Unknown fusion method: {method!r}")


# ---------------------------------------------------------------------------
# ModelScorer Engine
# ---------------------------------------------------------------------------


class ModelScorer:
    """Loaded ONNX models, fusion metadata, and rule configuration for session scoring."""

    def __init__(
        self,
        *,
        mouse_model: LoadedModalityModel | None,
        keyboard_model: LoadedModalityModel | None,
        touch_model: LoadedModalityModel | None = None,
        fusion_metadata: LoadedFusionMetadata | None = None,
        rule_config: RuleConfig | None = None,
        fusion_method: str = "average",
        band_low_cutoff: float = 0.30,
        band_medium_cutoff: float = 0.70,
    ) -> None:
        self.mouse_model = mouse_model
        self.keyboard_model = keyboard_model
        self.touch_model = touch_model
        self.fusion_metadata = fusion_metadata
        self.rule_config = rule_config
        self.fusion_method = (
            fusion_metadata.default_method if fusion_metadata is not None else fusion_method
        )
        self.band_low_cutoff = band_low_cutoff
        self.band_medium_cutoff = band_medium_cutoff
        self._last_modality_features: dict[str, dict[str, float]] = {}

    @property
    def model_versions(self) -> ModelVersions:
        """Return the ``ModelVersions`` structure for API responses and health checks."""
        return ModelVersions(
            mouse=self.mouse_model.version_tag if self.mouse_model is not None else None,
            keyboard=(self.keyboard_model.version_tag if self.keyboard_model is not None else None),
            touch=self.touch_model.version_tag if self.touch_model is not None else None,
            fusion=self.fusion_metadata.version if self.fusion_metadata is not None else None,
        )

    def score_to_band(self, score: float) -> Band:
        """Map a numeric score in ``[0.0, 1.0]`` to ``'low'``, ``'medium'``, or ``'high'``."""
        if score < self.band_low_cutoff:
            return "low"
        if score < self.band_medium_cutoff:
            return "medium"
        return "high"

    def _run_onnx_windows(
        self,
        model: LoadedModalityModel,
        feature_windows: list[dict[str, float]],
    ) -> tuple[float, list[str]]:
        """Impute medians, run ONNX inference, calibrate, and compute top-3 features."""
        n_win = len(feature_windows)
        n_feat = len(model.feature_order)
        mat = np.empty((n_win, n_feat), dtype=np.float32)

        for row_idx, feat_dict in enumerate(feature_windows):
            for col_idx, feat_name in enumerate(model.feature_order):
                raw_val = feat_dict.get(feat_name, float("nan"))
                if raw_val is None or not math.isfinite(float(raw_val)):
                    mat[row_idx, col_idx] = np.float32(model.imputer_medians.get(feat_name, 0.0))
                else:
                    mat[row_idx, col_idx] = np.float32(raw_val)

        outputs = model.session.run([model.prob_output_name], {model.input_name: mat})
        probs_raw = outputs[0]
        if isinstance(probs_raw, list):
            pos_probs = [float(item[1]) for item in probs_raw]
        else:
            arr = np.asarray(probs_raw, dtype=np.float64)
            pos_probs = [float(arr[i, 1]) for i in range(arr.shape[0])]

        calibrated = [apply_calibration(p, model.calibration) for p in pos_probs]
        agg_score = float(np.mean(calibrated))

        # Average feature values across windows for top-3 attribution
        mean_features: dict[str, float] = {}
        for col_idx, feat_name in enumerate(model.feature_order):
            val = float(np.mean(mat[:, col_idx]))
            if math.isfinite(val):
                mean_features[feat_name] = round(val, 6)

        self._last_modality_features[model.modality] = mean_features
        top3 = top_k_contributing_features(mean_features, model, k=3)
        return agg_score, top3

    def score_mouse(
        self,
        mouse: MouseBehaviour | None,
        env: EnvSignals | None = None,
    ) -> tuple[float | None, list[str]]:
        """Extract features and score a mouse payload if sufficient events exist."""
        if mouse is None or self.mouse_model is None:
            return None, []
        include_shortcuts = "window_n_points" in self.mouse_model.feature_order
        windows = extract_mouse_feature_windows(
            mouse, env, include_shortcut_features=include_shortcuts
        )
        if not windows:
            return None, []
        return self._run_onnx_windows(self.mouse_model, windows)

    def score_keyboard(
        self,
        keys: KeyBehaviour | None,
    ) -> tuple[float | None, list[str]]:
        """Extract features and score a keyboard payload if sufficient events exist."""
        if keys is None or self.keyboard_model is None:
            return None, []
        feat_dict = extract_keyboard_feature_dict(keys)
        if feat_dict is None:
            return None, []
        return self._run_onnx_windows(self.keyboard_model, [feat_dict])

    def score(
        self,
        env: AssessRequest | EnvSignals | dict[str, Any] | None = None,
        behaviour: BehaviourPayload | dict[str, Any] | None = None,
        *,
        rate_limit_exceeded: bool = False,
        invalid_nonce_or_signature: bool = False,
        nonce_age_ms: float | None = None,
    ) -> ScoreResult:
        """Score a session's environment + behavioural signals and return a ``ScoreResult``."""
        if isinstance(env, AssessRequest):
            behaviour = env.behaviour
            env = env.env
        coerced_env: EnvSignals | None
        if env is None or isinstance(env, EnvSignals):
            coerced_env = env
        else:
            coerced_env = EnvSignals(**env)

        coerced_beh: BehaviourPayload | None
        beh_dict: dict[str, Any] | None
        if behaviour is None:
            coerced_beh = None
            beh_dict = None
        elif isinstance(behaviour, BehaviourPayload):
            coerced_beh = behaviour
            beh_dict = behaviour.model_dump(exclude_none=True)
        else:
            coerced_beh = BehaviourPayload(**behaviour)
            beh_dict = behaviour

        weights = self.rule_config.weights if self.rule_config is not None else None
        enabled = self.rule_config.enabled if self.rule_config is not None else None

        rule_eval: RuleScore = evaluate_rule_score(
            coerced_env,
            beh_dict,
            weights=weights,
            enabled=enabled,
            rate_limit_exceeded=rate_limit_exceeded,
            invalid_nonce_or_signature=invalid_nonce_or_signature,
            nonce_age_ms=nonce_age_ms,
        )

        # Hard rule or invalid nonce/signature bypasses ML model inference immediately
        if rule_eval.model_bypassed:
            return ScoreResult(
                score=1.0,
                band="high",
                reasons=list(rule_eval.reasons),
                model_versions=self.model_versions,
                rule_score=rule_eval.rule_score,
                model_score=None,
                fired_rules=list(rule_eval.fired_rules),
                top_features={},
                degraded=False,
            )

        mouse_score: float | None = None
        keyboard_score: float | None = None
        touch_score: float | None = None
        top_features: dict[str, list[str]] = {}
        derived_features: dict[str, float] = {}
        degraded = False

        if coerced_beh is not None:
            try:
                if (
                    coerced_beh.mouse is not None
                    and len(coerced_beh.mouse.points) >= MIN_MOUSE_MOVE_POINTS
                ):
                    if self.mouse_model is None:
                        degraded = True
                    else:
                        mouse_score, mouse_top3 = self.score_mouse(coerced_beh.mouse, coerced_env)
                        if mouse_top3:
                            top_features["mouse"] = mouse_top3
                        for fk, fv in self._last_modality_features.get("mouse", {}).items():
                            derived_features[f"mouse:{fk}"] = fv

                if (
                    coerced_beh.keys is not None
                    and len(coerced_beh.keys.events) >= MIN_KEYBOARD_EVENTS
                ):
                    if self.keyboard_model is None:
                        degraded = True
                    else:
                        keyboard_score, kb_top3 = self.score_keyboard(coerced_beh.keys)
                        if kb_top3:
                            top_features["keyboard"] = kb_top3
                        for fk, fv in self._last_modality_features.get("keyboard", {}).items():
                            derived_features[f"keyboard:{fk}"] = fv
            except Exception:
                # Fail-safe (P5-05 / P5-11): model error falls back to rules-only with degraded=True
                mouse_score = None
                keyboard_score = None
                touch_score = None
                top_features = {}
                derived_features = {}
                degraded = True

        stacker_coeffs = (
            self.fusion_metadata.stacker_coefficients if self.fusion_metadata is not None else None
        )
        model_score = fuse_modality_scores(
            mouse_score,
            keyboard_score,
            touch_score,
            method=self.fusion_method,
            stacker_coefficients=stacker_coeffs,
        )

        if degraded or model_score is None:
            final_score = float(np.clip(rule_eval.rule_score, 0.0, 1.0))
        else:
            final_score = float(np.clip(max(model_score, rule_eval.rule_score), 0.0, 1.0))

        band = self.score_to_band(final_score)

        reasons: list[str] = list(rule_eval.reasons)
        for mod_feats in top_features.values():
            reasons.extend(mod_feats)

        return ScoreResult(
            score=final_score,
            band=band,
            reasons=reasons,
            model_versions=self.model_versions,
            rule_score=rule_eval.rule_score,
            model_score=model_score,
            mouse_score=mouse_score,
            keyboard_score=keyboard_score,
            touch_score=touch_score,
            fired_rules=list(rule_eval.fired_rules),
            top_features=top_features,
            derived_features=derived_features,
            degraded=degraded,
        )

    def score_request(
        self,
        request: AssessRequest,
        *,
        rate_limit_exceeded: bool = False,
        invalid_nonce_or_signature: bool = False,
        nonce_age_ms: float | None = None,
    ) -> ScoreResult:
        """Convenience wrapper to score a validated ``AssessRequest``."""
        return self.score(
            request.env,
            request.behaviour,
            rate_limit_exceeded=rate_limit_exceeded,
            invalid_nonce_or_signature=invalid_nonce_or_signature,
            nonce_age_ms=nonce_age_ms,
        )


def load_scorer(
    models_dir: Path,
    *,
    rule_config: RuleConfig | None = None,
    fusion_method: str = "average",
    mouse_subdir: str = "mouse-v1",
    keyboard_subdir: str = "keyboard-v1",
    touch_subdir: str = "touch-v1",
    fusion_subdir: str = "fusion-v1",
    strict: bool = True,
) -> ModelScorer:
    """Load ONNX models and fusion metadata once at startup.

    Args:
        models_dir: Root directory containing ``mouse-v1/``, ``keyboard-v1/``,
            ``fusion-v1/``, and optional ``touch-v1/``.
        rule_config: Optional validated :class:`RuleConfig`.
        fusion_method: Multimodal fusion rule (``"average"``, ``"noisy_or"``,
            ``"stacker"``).
        strict: When ``True`` (default), raises :class:`ModelMetadataError` if
            required mouse, keyboard, or fusion artifacts are missing or invalid.

    Returns:
        A configured :class:`ModelScorer` instance.
    """
    mouse_dir = models_dir / mouse_subdir
    keyboard_dir = models_dir / keyboard_subdir
    touch_dir = models_dir / touch_subdir
    fusion_dir = models_dir / fusion_subdir

    mouse_model: LoadedModalityModel | None = None
    keyboard_model: LoadedModalityModel | None = None
    touch_model: LoadedModalityModel | None = None
    fusion_meta: LoadedFusionMetadata | None = None

    if strict or (mouse_dir / "model.onnx").exists():
        mouse_model = load_modality_model(
            mouse_dir, "mouse", expected_features=EXPECTED_MOUSE_FEATURE_NAMES
        )

    if strict or (keyboard_dir / "model.onnx").exists():
        keyboard_model = load_modality_model(
            keyboard_dir, "keyboard", expected_features=EXPECTED_KEYBOARD_FEATURE_NAMES
        )

    if (touch_dir / "model.onnx").exists() and (touch_dir / "metadata.json").exists():
        touch_model = load_modality_model(touch_dir, "touch")

    if strict or (fusion_dir / "metadata.json").exists():
        fusion_meta = load_fusion_metadata(fusion_dir, default_method=fusion_method)

    return ModelScorer(
        mouse_model=mouse_model,
        keyboard_model=keyboard_model,
        touch_model=touch_model,
        fusion_metadata=fusion_meta,
        rule_config=rule_config,
        fusion_method=fusion_method,
    )
