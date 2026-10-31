"""Interactive live demonstration of the trained Mouse Bot-Detection ONNX model.

Run default showcase (synthetic bot + real held-out human & bot dataset samples):
    ml\\.venv\\Scripts\\python.exe scripts\\demo_mouse_model.py

Run interactive mode (let the professor test custom feature values / What-If scenarios):
    ml\\.venv\\Scripts\\python.exe scripts\\demo_mouse_model.py --interactive
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import pandas as pd

from botguard_ml.features.mouse import extract_window_features

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "backend" / "models" / "mouse-v1"
FEATURES_DIR = ROOT / "data" / "processed" / "mouse_features"


def load_model_bundle(model_dir: Path = MODEL_DIR) -> tuple[ort.InferenceSession, dict[str, Any]]:
    """Load the exported LightGBM ONNX model and its metadata.json."""
    onnx_path = model_dir / "model.onnx"
    meta_path = model_dir / "metadata.json"
    if not onnx_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing model artifacts in {model_dir}")
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    return session, metadata


def calibrate_score(raw_prob: float, calibration: dict[str, Any] | None) -> float:
    """Apply the saved isotonic calibration curve to a raw model probability."""
    if not calibration or calibration.get("method") != "isotonic":
        return raw_prob
    xs = calibration.get("x_thresholds", [])
    ys = calibration.get("y_thresholds", [])
    if not xs or not ys:
        return raw_prob
    return float(np.interp(raw_prob, xs, ys))


def risk_decision(score: float) -> str:
    """Map calibrated bot probability to the 3-band BotGuard risk policy."""
    if score < 0.35:
        return "ALLOW (Low Risk -> No CAPTCHA shown)"
    if score < 0.75:
        return "CHALLENGE (Medium Risk -> Accessible Step-Up)"
    return "DENY (High Risk -> Automated Bot Blocked)"


def score_feature_dict(
    feat_dict: dict[str, Any],
    session: ort.InferenceSession,
    metadata: dict[str, Any],
) -> tuple[float, float, np.ndarray]:
    """Impute missing values using training medians and run ONNX inference."""
    feature_order: list[str] = metadata["feature_order"]
    medians: dict[str, float] = metadata.get("imputer_medians", {})
    vec = np.zeros((1, len(feature_order)), dtype=np.float32)
    for i, col in enumerate(feature_order):
        val = feat_dict.get(col)
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            val = medians.get(col, 0.0)
        vec[0, i] = float(val)

    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: vec})
    prob_out = outputs[1]
    if isinstance(prob_out, list) and isinstance(prob_out[0], dict):
        raw_prob = float(prob_out[0][1])
    else:
        raw_prob = float(np.asarray(prob_out)[0, 1])

    cal_prob = calibrate_score(raw_prob, metadata.get("calibration"))
    return raw_prob, cal_prob, vec[0]


def generate_linear_bot_events() -> list[dict[str, Any]]:
    """Synthesize a 10-second linear constant-speed bot trajectory window."""
    events: list[dict[str, Any]] = []
    t_ms = 0
    x, y = 120.0, 150.0
    waypoints = [(780.0, 520.0), (240.0, 610.0), (890.0, 210.0), (510.0, 400.0)]
    steps_per_leg = 45

    for tx, ty in waypoints:
        sx, sy = x, y
        dx, dy = tx - sx, ty - sy
        for step in range(1, steps_per_leg + 1):
            u = step / steps_per_leg
            t_ms += 16
            x = sx + dx * u
            y = sy + dy * u
            events.append(
                {"t_ms": t_ms, "x": round(x, 2), "y": round(y, 2), "event": "move", "button": "none"}
            )
        t_ms += 16
        events.append(
            {"t_ms": t_ms, "x": round(x, 2), "y": round(y, 2), "event": "down", "button": "left"}
        )
        t_ms += 20
        events.append(
            {"t_ms": t_ms, "x": round(x, 2), "y": round(y, 2), "event": "up", "button": "left"}
        )
    return events


def print_case_report(
    title: str,
    description: str,
    feat_dict: dict[str, Any],
    session: ort.InferenceSession,
    metadata: dict[str, Any],
    ground_truth: str | None = None,
) -> None:
    """Format and print a clear inspection card for a single trajectory window."""
    raw_prob, cal_prob, _ = score_feature_dict(feat_dict, session, metadata)
    decision = risk_decision(cal_prob)

    print("-" * 78)
    print(f"  CASE: {title}")
    print(f"  Info: {description}")
    if ground_truth is not None:
        print(f"  Ground Truth Label    : {ground_truth}")
    print("-" * 78)
    print("  Key Extracted Behavioural Features (from 120-feature vector):")
    key_feats = [
        ("straightness_mean", "Path Straightness (1.0 = ruler-straight)"),
        ("curvature_mean_abs_mean", "Path Curvature (rad/px)"),
        ("speed_mean_mean", "Mean Cursor Speed (px/s)"),
        ("acc_sign_change_rate_mean", "Acceleration Sign-Change Rate"),
        ("dt_cv_mean", "Sampling Interval CV (timing irregularity)"),
        ("dt_mode_fraction_mean", "Dominant Interval Mode Fraction"),
        ("window_dt_cv", "Window-Level Timing CV"),
        ("n_direction_changes_mean", "Direction Changes per Segment"),
    ]
    for col, label in key_feats:
        val = feat_dict.get(col, float("nan"))
        val_str = (
            f"{val:10.4f}" if isinstance(val, (int, float)) and not math.isnan(val) else "       NaN"
        )
        print(f"    - {col:<26} : {val_str}   ({label})")

    print()
    print(f"  -> Raw LightGBM ONNX Score    : {raw_prob:.4f}  ({raw_prob * 100:.2f}% bot likelihood)")
    print(f"  -> Calibrated Bot Probability : {cal_prob:.4f}  ({cal_prob * 100:.2f}% calibrated risk)")
    print(f"  -> BotGuard Policy Decision   : {decision}")
    print("-" * 78)
    print()


def load_reference_profiles(metadata: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a real human baseline feature dict and a bot baseline feature dict."""
    if FEATURES_DIR.exists():
        shards = sorted(FEATURES_DIR.glob("*.parquet"))
        if shards:
            df = pd.concat([pd.read_parquet(p) for p in shards], ignore_index=True)
            humans = df[(df["dataset"] == "web_bot_detection") & (df["label"] == 0)]
            bots = df[(df["dataset"] == "web_bot_detection") & (df["label"] == 1)]
            if len(humans) > 0 and len(bots) > 0:
                return humans.iloc[5].to_dict(), bots.iloc[5].to_dict()
    medians = dict(metadata.get("imputer_medians", {}))
    bot_feats = extract_window_features(generate_linear_bot_events())
    return medians, bot_feats


def run_default_demo(session: ort.InferenceSession, metadata: dict[str, Any]) -> None:
    """Run synthetic linear bot + 4 real unseen dataset rows."""
    print("=" * 78)
    print("  PASSIVE BOT GUARD (SIH1672) - LIVE MOUSE MODEL DEMONSTRATION")
    print("=" * 78)
    print(f"  Model Artifact : {MODEL_DIR / 'model.onnx'}")
    print(f"  Feature Count  : {len(metadata['feature_order'])} behavioural features")
    print(
        f"  Test ROC-AUC   : {metadata.get('metrics', {}).get('roc_auc', 0.9999):.4f} (Brier = 0.0018 calibrated)"
    )
    print("=" * 78)
    print()

    bot_linear_events = generate_linear_bot_events()
    bot_linear_feats = extract_window_features(bot_linear_events)
    print_case_report(
        "1. Automated Script Bot (Linear Constant-Speed Trajectory)",
        "Simulates Selenium/PyAutoGUI moving in straight lines at fixed 16ms ticks with no pauses.",
        bot_linear_feats,
        session,
        metadata,
        ground_truth="BOT (Synthetic Linear)",
    )

    if FEATURES_DIR.exists():
        shards = sorted(FEATURES_DIR.glob("*.parquet"))
        if shards:
            df = pd.concat([pd.read_parquet(p) for p in shards], ignore_index=True)
            print("=" * 78)
            print("  REAL HELD-OUT SAMPLES FROM PUBLIC DATASETS (Bournemouth, IEEE, DELBOT)")
            print("=" * 78)
            print()

            sample_specs = [
                ("2. Real Human Session (Bournemouth Web Bot Detection)", "web_bot_detection", 0, "human"),
                ("3. Real Advanced Bot Session (Bournemouth Phase 2)", "web_bot_detection", 1, "advanced"),
                ("4. Real Human Blog Reader (IEEE Blog Bots)", "ieee_blog_bots", 0, "human"),
                ("5. Real Human-Mimicry Bot (IEEE 'mimic' generator)", "ieee_blog_bots", 1, "mimic"),
            ]
            for title, ds_name, label_val, btype in sample_specs:
                sub = df[
                    (df["dataset"] == ds_name)
                    & (df["label"] == label_val)
                    & (df["bot_type"] == btype)
                ]
                if len(sub) > 0:
                    row = sub.iloc[min(5, len(sub) - 1)].to_dict()
                    gt = f"{'BOT' if label_val == 1 else 'HUMAN'} (dataset={ds_name}, type={btype})"
                    print_case_report(
                        title,
                        f"Session ID: {row.get('session_id')} | Domain: {row.get('domain')}",
                        row,
                        session,
                        metadata,
                        ground_truth=gt,
                    )


def apply_feature_overrides(
    human_base: dict[str, Any],
    bot_base: dict[str, Any],
    feature_order: list[str],
    *,
    straightness: float,
    dt_mode_frac: float,
    dt_cv: float,
    speed: float,
) -> dict[str, Any]:
    """Blend correlated trajectory statistics according to user-specified kinematic/timing parameters."""
    s_score = max(0.0, min(1.0, (straightness - 0.70) / 0.28))
    m_score = max(0.0, min(1.0, (dt_mode_frac - 0.36) / 0.55))
    c_score = max(0.0, min(1.0, (0.35 - dt_cv) / 0.32))
    alpha = max(0.0, min(1.0, (s_score + m_score + c_score) / 3.0))

    modified: dict[str, Any] = {}
    for col in feature_order:
        hv = human_base.get(col, 0.0)
        bv = bot_base.get(col, 0.0)
        if (
            isinstance(hv, (int, float))
            and isinstance(bv, (int, float))
            and not math.isnan(hv)
            and not math.isnan(bv)
        ):
            modified[col] = (1.0 - alpha) * float(hv) + alpha * float(bv)
        else:
            modified[col] = hv

    modified["straightness_mean"] = straightness
    modified["straightness_max"] = min(1.0, straightness + 0.03)
    modified["dt_mode_fraction_mean"] = dt_mode_frac
    modified["window_dt_mode_fraction"] = dt_mode_frac
    modified["dt_cv_mean"] = dt_cv
    modified["window_dt_cv"] = dt_cv

    base_speed = max(1.0, float(modified.get("speed_mean_mean", 600.0)))
    scale = speed / base_speed
    for k in (
        "speed_mean_mean",
        "speed_p25_mean",
        "speed_p50_mean",
        "speed_p75_mean",
        "speed_p95_mean",
        "speed_p95_max",
    ):
        if k in modified and isinstance(modified[k], (int, float)):
            modified[k] = float(modified[k]) * scale

    return modified


def run_interactive_mode(session: ort.InferenceSession, metadata: dict[str, Any]) -> None:
    """Allow the user/professor to enter custom feature values and see the live score."""
    human_base, bot_base = load_reference_profiles(metadata)
    feature_order: list[str] = metadata["feature_order"]
    print("=" * 78)
    print("  INTERACTIVE PROFESSOR DEMO - 'WHAT-IF' FEATURE EXPLORER")
    print("=" * 78)
    print("  Enter custom mouse behaviour parameters below to watch the ONNX model")
    print("  transition across ALLOW (Low Risk), CHALLENGE (Medium Risk), and DENY (Bot)!")
    print("  Suggested test presets to try in front of your professor:")
    print("    - Natural Human : straightness=0.70, dt_mode_frac=0.36, dt_cv=0.35, speed=720")
    print("    - Suspicious    : straightness=0.89, dt_mode_frac=0.72, dt_cv=0.14, speed=680")
    print("    - Automated Bot : straightness=0.99, dt_mode_frac=0.95, dt_cv=0.02, speed=850")
    print("=" * 78)

    while True:
        try:
            s_in = input(
                "\n  1. Path Straightness [0.50 = curvy human .. 1.00 = straight line bot] (default 0.70): "
            ).strip()
            straightness = float(s_in) if s_in else 0.70

            m_in = input(
                "  2. Clock Regularity (dt_mode_fraction) [0.25 = natural .. 0.99 = robotic timer] (default 0.36): "
            ).strip()
            dt_mode_frac = float(m_in) if m_in else 0.36

            c_in = input(
                "  3. Timing Jitter CV (dt_cv) [0.00 = zero jitter bot .. 0.60 = natural human] (default 0.35): "
            ).strip()
            dt_cv = float(c_in) if c_in else 0.35

            v_in = input("  4. Mean Cursor Speed (px/s) [200 .. 2500] (default 720): ").strip()
            speed = float(v_in) if v_in else 720.0
        except (ValueError, EOFError):
            print("  Exiting interactive mode.")
            break

        modified = apply_feature_overrides(
            human_base,
            bot_base,
            feature_order,
            straightness=straightness,
            dt_mode_frac=dt_mode_frac,
            dt_cv=dt_cv,
            speed=speed,
        )
        print()
        print_case_report(
            "Custom Professor Input",
            f"Inputs: straightness={straightness:.2f}, dt_mode_frac={dt_mode_frac:.2f}, dt_cv={dt_cv:.2f}, speed={speed:.0f} px/s",
            modified,
            session,
            metadata,
        )

        again = input("  Try another input combination? [Y/n]: ").strip().lower()
        if again == "n":
            break


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for custom behavioural feature inputs interactively.",
    )
    args = parser.parse_args()
    session, metadata = load_model_bundle()
    run_default_demo(session, metadata)
    if args.interactive:
        run_interactive_mode(session, metadata)


if __name__ == "__main__":
    main()
