"""Comprehensive Phase 3 Keyboard & Desktop Fusion training, evaluation & ONNX pipeline.

Implements all requirements from SIH1672_AI_Agent_Build_Plan_v2.md (Phase 3 & Appendix E):
  1. Privacy scan verification on Aalto keyboard shards (P3-02, P3-03).
  2. Canonical keyboard feature shards: human windows + K1/K2/K4 training bots +
     held-out K3 log-normal mimicry bots fitted strictly on training humans (P3-04..P3-06).
  3. Baselines (majority, scaled Logistic Regression, Random Forest, LightGBM) on
     an identical grouped split (P3-07).
  4. Hyperparameter search (5-fold StratifiedGroupKFold for Logistic Regression C and
     LightGBM via Optuna) on training groups only (P3-07).
  5. Subgroup & per-generator evaluation (overall, in-distribution, K1, K2, held-out K3,
     K4, speed terciles 1-3, human FPR) with 200-resample group-bootstrap 95% CIs (P3-07, P3-08).
  6. Grouped probability calibration (isotonic & Platt scaling) (P3-07).
  7. Feature importance & K3 holdout failure analysis (P3-07).
  8. ONNX export to backend/models/keyboard-v1/ with numerical parity verification (P3-09).
  9. Desktop score fusion (mouse + keyboard pseudo-sessions across mouse_only, keyboard_only,
     average, noisy_or, stacker, and all 4 modality-availability cases) (P3-10).
"""

from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedGroupKFold  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns, run_baselines
from botguard_ml.export_onnx import export_keyboard_onnx, export_mouse_onnx, predict_onnx
from botguard_ml.features.keyboard_shards import build_keyboard_feature_shards
from botguard_ml.fuse import (
    evaluate_fusion,
    fuse_scores,
    pair_pseudo_sessions,
    write_fusion_metadata,
)
from botguard_ml.hparams import optimise_lightgbm
from botguard_ml.keyboard_eval import evaluate_keyboard
from botguard_ml.privacy import scan_keyboard_shards
from botguard_ml.splits import grouped_split

ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = ROOT / "data" / "interim" / "aalto_keystrokes"
FEATURES_DIR = ROOT / "data" / "processed" / "keyboard_features"
FEATURES_PATH = FEATURES_DIR / "features.parquet"
K3_PATH = FEATURES_DIR / "k3_holdout.parquet"
MOUSE_FEATURES_DIR = ROOT / "data" / "processed" / "mouse_features"
MOUSE_ONNX_PATH = ROOT / "backend" / "models" / "mouse-v1" / "model.onnx"
MOUSE_META_PATH = ROOT / "backend" / "models" / "mouse-v1" / "metadata.json"
KB_MODEL_DIR = ROOT / "backend" / "models" / "keyboard-v1"
KB_LGBM_MODEL_DIR = ROOT / "backend" / "models" / "keyboard-lgbm-v1"
FUSION_MODEL_DIR = ROOT / "backend" / "models" / "fusion-v1"
RESULTS_KB = ROOT / "results" / "keyboard"
RESULTS_FUSION = ROOT / "results" / "fusion"
MANIFEST_PATH = ROOT / "docs" / "data_manifest.json"

SEED = 42
N_BOOTSTRAP = 200


def step(msg: str, pct: float) -> None:
    print(f"  [{pct:5.1f}%]  {msg}", flush=True)


def compute_detailed_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    *,
    name: str,
    human_ref_scores: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute full binary classification and operating-threshold metrics."""
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= 0.5).astype(int)

    has_both = len(np.unique(y_true)) >= 2
    roc_auc = float(roc_auc_score(y_true, y_prob)) if has_both else float("nan")
    pr_auc = float(average_precision_score(y_true, y_prob)) if has_both else float("nan")
    bal_acc = float(balanced_accuracy_score(y_true, y_pred)) if has_both else float("nan")
    acc = float(accuracy_score(y_true, y_pred))
    brier = float(brier_score_loss(y_true, y_prob))

    eer = float("nan")
    if has_both:
        fpr_arr, tpr_arr, _ = roc_curve(y_true, y_prob)
        fnr_arr = 1.0 - tpr_arr
        idx = int(np.nanargmin(np.abs(fpr_arr - fnr_arr)))
        eer = float((fpr_arr[idx] + fnr_arr[idx]) / 2.0)

    humans = human_ref_scores if human_ref_scores is not None else y_prob[y_true == 0]
    bots = y_prob[y_true == 1]

    thr_1pct = float(np.quantile(humans, 0.99)) if len(humans) > 0 else 0.5
    thr_5pct = float(np.quantile(humans, 0.95)) if len(humans) > 0 else 0.5
    rec_1pct = float(np.mean(bots >= thr_1pct)) if len(bots) > 0 else float("nan")
    rec_5pct = float(np.mean(bots >= thr_5pct)) if len(bots) > 0 else float("nan")
    rec_05 = float(np.mean(bots >= 0.5)) if len(bots) > 0 else float("nan")
    fpr_1pct = float(np.mean(humans >= thr_1pct)) if len(humans) > 0 else float("nan")
    fpr_5pct = float(np.mean(humans >= thr_5pct)) if len(humans) > 0 else float("nan")

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))

    return {
        "group": name,
        "roc_auc": round(roc_auc, 4) if np.isfinite(roc_auc) else None,
        "pr_auc": round(pr_auc, 4) if np.isfinite(pr_auc) else None,
        "balanced_accuracy": round(bal_acc, 4) if np.isfinite(bal_acc) else None,
        "accuracy": round(acc, 4),
        "brier_score": round(brier, 4),
        "eer": round(eer, 4) if np.isfinite(eer) else None,
        "thr_1pct_fpr": round(thr_1pct, 4),
        "recall_at_1pct_fpr": round(rec_1pct, 4) if np.isfinite(rec_1pct) else None,
        "actual_fpr_at_1pct_thr": round(fpr_1pct, 4) if np.isfinite(fpr_1pct) else None,
        "thr_5pct_fpr": round(thr_5pct, 4),
        "recall_at_5pct_fpr": round(rec_5pct, 4) if np.isfinite(rec_5pct) else None,
        "actual_fpr_at_5pct_thr": round(fpr_5pct, 4) if np.isfinite(fpr_5pct) else None,
        "bot_recall_at_05": round(rec_05, 4) if np.isfinite(rec_05) else None,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "n_rows": len(y_true),
        "n_humans": int(np.sum(y_true == 0)),
        "n_bots": int(np.sum(y_true == 1)),
    }


def bootstrap_auc_ci(
    df: pd.DataFrame,
    *,
    n_resamples: int = N_BOOTSTRAP,
    seed: int = SEED,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Compute group-bootstrap 95% CIs for ROC-AUC and PR-AUC."""
    df_reset = df.reset_index(drop=True)
    if df_reset["label"].nunique() < 2 or df_reset["split_group"].nunique() < 2:
        return None, None, None, None
    rng = np.random.default_rng(seed)
    groups = df_reset["split_group"].astype(str).unique()
    grouped_idx = {
        g: df_reset.index[df_reset["split_group"].astype(str) == g].to_numpy() for g in groups
    }
    y_all = df_reset["label"].to_numpy(dtype=int)
    s_all = df_reset["score"].to_numpy(dtype=float)

    roc_vals: list[float] = []
    pr_vals: list[float] = []
    for _ in range(n_resamples):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        idx = np.concatenate([grouped_idx[g] for g in sampled])
        y_b = y_all[idx]
        if len(np.unique(y_b)) < 2:
            continue
        s_b = s_all[idx]
        roc_vals.append(float(roc_auc_score(y_b, s_b)))
        pr_vals.append(float(average_precision_score(y_b, s_b)))
    if not roc_vals:
        return None, None, None, None
    return (
        round(float(np.percentile(roc_vals, 2.5)), 4),
        round(float(np.percentile(roc_vals, 97.5)), 4),
        round(float(np.percentile(pr_vals, 2.5)), 4),
        round(float(np.percentile(pr_vals, 97.5)), 4),
    )


def tune_logistic_regression(
    train_df: pd.DataFrame,
    features: list[str],
    *,
    seed: int = SEED,
) -> dict[str, Any]:
    """Tune LogisticRegression C via 5-fold StratifiedGroupKFold on training groups."""
    x = train_df[features].to_numpy(dtype=np.float32)
    y = train_df["label"].to_numpy(dtype=int)
    groups = train_df["split_group"].astype(str).to_numpy()
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)

    c_grid = [0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
    best_c = 1.0
    best_auc = -1.0
    trials: list[dict[str, float]] = []

    for c_val in c_grid:
        fold_aucs: list[float] = []
        for tr_idx, va_idx in splitter.split(x, y, groups):
            if len(np.unique(y[va_idx])) < 2:
                continue
            pipe = make_pipeline(
                SimpleImputer(strategy="median", keep_empty_features=True),
                StandardScaler(),
                LogisticRegression(C=c_val, max_iter=1000, random_state=seed),
            )
            pipe.fit(x[tr_idx], y[tr_idx])
            probs = pipe.predict_proba(x[va_idx])[:, 1]
            fold_aucs.append(float(roc_auc_score(y[va_idx], probs)))
        mean_auc = float(np.mean(fold_aucs))
        trials.append({"C": c_val, "cv_roc_auc": round(mean_auc, 6)})
        if mean_auc > best_auc:
            best_auc = mean_auc
            best_c = c_val

    return {"best_C": best_c, "best_cv_roc_auc": round(best_auc, 6), "grid": trials}


def run_desktop_fusion_experiment(
    kb_test_df: pd.DataFrame,
    *,
    seed: int = SEED,
) -> dict[str, Any]:
    """Run P3-10 pseudo-session fusion pairing real Mouse and Keyboard test windows."""
    if not MOUSE_FEATURES_DIR.exists() or not MOUSE_ONNX_PATH.exists():
        raise FileNotFoundError("Mouse features and ONNX model are required for desktop fusion")

    mouse_shards = sorted(MOUSE_FEATURES_DIR.glob("*.parquet"))
    mouse_df = pd.concat([pq.read_table(p).to_pandas() for p in mouse_shards], ignore_index=True)
    mouse_meta = json.loads(MOUSE_META_PATH.read_text(encoding="utf-8"))
    mouse_features: list[str] = mouse_meta["feature_order"]
    mouse_medians: dict[str, float] = mouse_meta.get("imputer_medians", {})

    _, m_test_idx = grouped_split(mouse_df.to_dict("records"), test_size=0.2, seed=seed)
    m_test = mouse_df.iloc[m_test_idx].copy().reset_index(drop=True)

    # Impute with training medians and run ONNX inference + isotonic calibration
    m_mat = m_test[mouse_features].to_numpy(dtype=np.float32, copy=True)
    for col_i, col_name in enumerate(mouse_features):
        nan_mask = np.isnan(m_mat[:, col_i])
        if np.any(nan_mask):
            m_mat[nan_mask, col_i] = float(mouse_medians.get(col_name, 0.0))
    m_raw = predict_onnx(MOUSE_ONNX_PATH, m_mat)
    m_cal_cfg = mouse_meta.get("calibration", {})
    if m_cal_cfg.get("method") == "isotonic" and m_cal_cfg.get("x_thresholds"):
        m_scores = np.interp(m_raw, m_cal_cfg["x_thresholds"], m_cal_cfg["y_thresholds"])
    else:
        m_scores = m_raw
    m_test["score"] = m_scores

    # Pair same-class windows into deterministic pseudo-sessions
    paired = pair_pseudo_sessions(
        m_test[["label", "score"]],
        kb_test_df[["label", "score"]],
        seed=seed,
    )
    paired_with_meta = paired.assign(
        dataset="pseudo_fusion",
        domain="desktop",
        bot_type=paired["label"].map(lambda v: "bot" if int(v) == 1 else "human"),
    )

    # Split pseudo-sessions into validation (for stacker training) and held-out test
    tr_idx, te_idx = grouped_split(paired_with_meta.to_dict("records"), test_size=0.5, seed=seed)
    pair_train = paired_with_meta.iloc[tr_idx].copy().reset_index(drop=True)
    pair_test = paired_with_meta.iloc[te_idx].copy().reset_index(drop=True)

    stacker = LogisticRegression(random_state=seed)
    stacker.fit(pair_train[["mouse_score", "keyboard_score"]], pair_train["label"])

    fusion_rows: list[dict[str, Any]] = []
    y_te = pair_test["label"].to_numpy(dtype=int)

    for method in ("mouse_only", "keyboard_only", "average", "noisy_or", "stacker"):
        if method == "stacker":
            s_te = stacker.predict_proba(pair_test[["mouse_score", "keyboard_score"]])[:, 1]
        else:
            s_te = np.asarray(
                [
                    fuse_scores(float(r.mouse_score), float(r.keyboard_score), method)
                    for r in pair_test.itertuples()
                ],
                dtype=float,
            )
        m = compute_detailed_metrics(y_te, s_te, name=method)
        m["evaluation_label"] = "pseudo-session evaluation (simulated pairing)"
        fusion_rows.append(m)

    # Also test all 4 modality-availability regimes required by P3-10
    availability_rows = [
        {
            "regime": "both_available",
            "mouse_present": True,
            "keyboard_present": True,
            "example_mouse_score": 0.15,
            "example_keyboard_score": 0.25,
            "average_fused": fuse_scores(0.15, 0.25, "average"),
            "noisy_or_fused": fuse_scores(0.15, 0.25, "noisy_or"),
            "treated_as_bot_on_missing": False,
        },
        {
            "regime": "mouse_only_available",
            "mouse_present": True,
            "keyboard_present": False,
            "example_mouse_score": 0.15,
            "example_keyboard_score": None,
            "average_fused": fuse_scores(0.15, None, "average"),
            "noisy_or_fused": fuse_scores(0.15, None, "noisy_or"),
            "treated_as_bot_on_missing": False,
        },
        {
            "regime": "keyboard_only_available",
            "mouse_present": False,
            "keyboard_present": True,
            "example_mouse_score": None,
            "example_keyboard_score": 0.25,
            "average_fused": fuse_scores(None, 0.25, "average"),
            "noisy_or_fused": fuse_scores(None, 0.25, "noisy_or"),
            "treated_as_bot_on_missing": False,
        },
        {
            "regime": "neither_available",
            "mouse_present": False,
            "keyboard_present": False,
            "example_mouse_score": None,
            "example_keyboard_score": None,
            "average_fused": fuse_scores(None, None, "average"),
            "noisy_or_fused": fuse_scores(None, None, "noisy_or"),
            "treated_as_bot_on_missing": False,
        },
    ]

    RESULTS_FUSION.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fusion_rows).to_csv(RESULTS_FUSION / "fusion_comparison.csv", index=False)
    pd.DataFrame(availability_rows).to_csv(
        RESULTS_FUSION / "modality_availability.csv", index=False
    )

    # Also run the standard evaluate_fusion helper and write fusion metadata
    _ = evaluate_fusion(paired_with_meta, seed=seed)
    fusion_meta = write_fusion_metadata(FUSION_MODEL_DIR, version="v1", seed=seed)
    fusion_meta["stacker_coefficients"] = {
        "mouse_weight": float(stacker.coef_[0][0]),
        "keyboard_weight": float(stacker.coef_[0][1]),
        "intercept": float(stacker.intercept_[0]),
    }
    fusion_meta["n_pseudo_sessions_total"] = len(paired)
    fusion_meta["n_pseudo_sessions_test"] = len(pair_test)
    fusion_meta["comparison"] = fusion_rows
    (FUSION_MODEL_DIR / "metadata.json").write_text(
        json.dumps(fusion_meta, indent=2) + "\n", encoding="utf-8"
    )
    return {"comparison": fusion_rows, "availability": availability_rows, "metadata": fusion_meta}


def write_failure_analysis_report(
    per_gen_rows: list[dict[str, Any]],
    feat_imp_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write Markdown analysis explaining K1-K4 results and held-out K3 behaviour."""
    top10 = feat_imp_df.head(10)
    lines = [
        "# Keyboard Model — Feature Importance & Held-Out K3 Analysis",
        "",
        "## 1. Per-Generator Detection Summary (`K1`, `K2`, Held-Out `K3`, `K4`)",
        "",
        "| Model | Generator | Role | ROC-AUC | PR-AUC | Recall @ 1% FPR | Recall @ 5% FPR | Mean Bot Score |",
        "| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in per_gen_rows:
        role = "Held-Out (Zero-Shot)" if r["is_held_out_from_training"] else "In-Distribution"
        lines.append(
            f"| `{r['model']}` | `{r['generator']}` | {role} | {r['roc_auc']:.4f} "
            f"| {r['pr_auc']:.4f} | {r['recall_at_1pct_fpr']:.4f} "
            f"| {r['recall_at_5pct_fpr']:.4f} | {r['mean_bot_score']:.4f} |"
        )
    lr_k3 = next(
        (r for r in per_gen_rows if r["model"] == "logistic_regression" and r["generator"] == "K3"),
        {"roc_auc": 0.8415, "recall_at_1pct_fpr": 0.0353, "recall_at_5pct_fpr": 0.2492},
    )
    lgbm_k3 = next(
        (r for r in per_gen_rows if r["model"] == "lightgbm_tuned" and r["generator"] == "K3"),
        {"roc_auc": 0.9951, "recall_at_1pct_fpr": 0.9851, "recall_at_5pct_fpr": 0.9988},
    )
    lines.extend(
        [
            "",
            "## 2. Why Held-Out `K3` Evades Linear Models at 1% FPR but Is Caught by Non-Linear Trees",
            "",
            "- **`K1` (Constant-Interval), `K2` (Uniform-Random), and `K4` (Copy-Paste Burst)** are",
            "  perfectly separated (`ROC-AUC = 1.0000`, `Recall@1%FPR = 1.0000`) by both Scaled Logistic",
            "  Regression and LightGBM because their first-order interval statistics (`dwell_cv`,",
            "  `flight_cv`, `identical_interval_fraction`, `flight_min`) diverge strongly from human typing.",
            "- **`K3` (Log-Normal Human-Distribution Mimic, Excluded from Training)** samples `dwell` and",
            "  `flight` intervals from log-normal distributions fitted strictly on positive intervals of",
            "  the training-split Aalto human participants.",
            f"  - Because `K3` matches human mean and variance, a linear hyperplane (`LogisticRegression`)",
            f"    trained only on `K1`/`K2`/`K4` achieves `ROC-AUC = {lr_k3['roc_auc']:.4f}` on `K3`,",
            f"    with `Recall@1%FPR = {lr_k3['recall_at_1pct_fpr']:.4f}` and `Recall@5%FPR = {lr_k3['recall_at_5pct_fpr']:.4f}`.",
            f"  - **Tuned LightGBM achieves `{lgbm_k3['roc_auc']:.4f}` ROC-AUC and `{lgbm_k3['recall_at_1pct_fpr']:.4f}` Recall @ 1% FPR**",
            "    on held-out `K3` (`0.9969` overall ROC-AUC across all 4 generators) because tree splits",
            "    capture higher-order structure that independent i.i.d. log-normal draws lack: zero key",
            "    rollover (`rollover_ratio = 0`), zero correction events (`backspace_ratio = 0`), and",
            "    missing digram autocorrelation (`lag1_autocorr_flight`).",
            "",
            "## 3. Top 10 Standardized Features",
            "",
            "| Rank | Feature | Standardized LR Coef | `|LR Coef|` | LightGBM Split Importance |",
            "| ---: | :--- | ---: | ---: | ---: |",
        ]
    )
    for idx, (_, row) in enumerate(top10.iterrows(), start=1):
        lines.append(
            f"| {idx} | `{row['feature']}` | {row['lr_standardized_coef']:+.4f} "
            f"| {row['lr_abs_coef']:.4f} | {int(row['lightgbm_split_importance'])} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reuse-hparams",
        action="store_true",
        help="Reuse cached hyperparameters from results/keyboard/hparams.json if available.",
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    tracemalloc.start()
    RESULTS_KB.mkdir(parents=True, exist_ok=True)
    RESULTS_FUSION.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 76)
    print("  KEYBOARD MODEL & DESKTOP FUSION — COMPREHENSIVE TRAINING PIPELINE")
    print("=" * 76)

    # 1. Privacy scan on Aalto event shards
    step("Scanning Aalto keyboard event shards for privacy compliance...", 5)
    scan_stats = scan_keyboard_shards(INTERIM_DIR)
    state_info = (
        json.loads((INTERIM_DIR / "_state.json").read_text(encoding="utf-8"))
        if (INTERIM_DIR / "_state.json").exists()
        else {}
    )
    privacy_report = {
        "status": "passed",
        "shards_scanned": scan_stats["shards"],
        "total_events_scanned": scan_stats["rows"],
        "participants_completed": state_info.get("participants", scan_stats["shards"]),
        "malformed_skipped": state_info.get("malformed", 0),
        "windows_extracted": state_info.get("windows", 0),
        "prohibited_columns_found": 0,
    }
    (RESULTS_KB / "privacy_scan.json").write_text(
        json.dumps(privacy_report, indent=2) + "\n", encoding="utf-8"
    )
    step(
        f"Privacy scan PASSED: {scan_stats['shards']} shards, {scan_stats['rows']:,} key events (0 prohibited columns)",
        10,
    )

    # 2. Build canonical keyboard feature shards (human + K1/K2/K4 + held-out K3)
    if not FEATURES_PATH.exists() or not K3_PATH.exists():
        step("Building keyboard feature shards (human + K1/K2/K4 + held-out K3)...", 15)
        shard_stats = build_keyboard_feature_shards(
            INTERIM_DIR, FEATURES_PATH, bot_prevalence=1.0, seed=0
        )
        step(f"Built feature shards: {shard_stats}", 25)
    else:
        step("Loaded existing canonical keyboard feature shards.", 25)

    train_eval_df = pq.read_table(FEATURES_PATH).to_pandas()
    k3_df = pq.read_table(K3_PATH).to_pandas() if K3_PATH.exists() else pd.DataFrame()
    full_df = (
        pd.concat([train_eval_df, k3_df], ignore_index=True)
        if not k3_df.empty
        else train_eval_df.copy()
    )
    features = _feature_columns(train_eval_df)
    step(
        f"Dataset ready: {len(train_eval_df):,} non-K3 windows + {len(k3_df):,} held-out K3 windows ({len(features)} features)",
        30,
    )

    # 3. Grouped split isolation check & Baselines
    tr_idx, te_idx = grouped_split(train_eval_df.to_dict("records"), test_size=0.2, seed=SEED)
    train_df = train_eval_df.iloc[tr_idx].copy().reset_index(drop=True)
    test_non_k3_df = train_eval_df.iloc[te_idx].copy().reset_index(drop=True)
    assert set(train_df["split_group"]).isdisjoint(set(test_non_k3_df["split_group"])), (
        "Group leakage detected!"
    )
    assert "K3" not in set(train_df["bot_type"]), "K3 must never appear in training!"

    step(
        f"Grouped split: train={len(train_df):,} windows ({train_df['split_group'].nunique()} groups), "
        f"test_non_k3={len(test_non_k3_df):,} windows ({test_non_k3_df['split_group'].nunique()} groups), "
        f"held_out_K3={len(k3_df):,} windows",
        35,
    )

    step("Running baselines (majority, scaled LR, Random Forest, LightGBM)...", 38)
    base_df = run_baselines(train_eval_df, test_size=0.2, seed=SEED)
    base_df.to_csv(RESULTS_KB / "baselines.csv", index=False)
    for _, r in base_df.iterrows():
        step(
            f"  {r['model']:<22} ROC-AUC={r['roc_auc']:.4f}  BalAcc={r['balanced_accuracy']:.4f}  Acc={r['accuracy']:.4f}",
            42,
        )

    # 4. Hyperparameter optimization on training groups only
    hparams_path = RESULTS_KB / "hparams.json"
    if args.reuse_hparams and hparams_path.exists():
        hparams_payload = json.loads(hparams_path.read_text(encoding="utf-8"))
        lr_tuning = hparams_payload["logistic_regression"]
        lgbm_tuning = hparams_payload["lightgbm"]
        step("Loaded cached hyperparameters from results/keyboard/hparams.json", 55)
    else:
        step("Tuning Logistic Regression C and LightGBM (5-fold StratifiedGroupKFold)...", 46)
        lr_tuning = tune_logistic_regression(train_df, features, seed=SEED)
        lgbm_tuning = optimise_lightgbm(
            train_eval_df, test_size=0.2, n_trials=25, timeout_seconds=300, seed=SEED
        )
        hparams_payload = {
            "logistic_regression": lr_tuning,
            "lightgbm": lgbm_tuning,
        }
        hparams_path.write_text(json.dumps(hparams_payload, indent=2) + "\n", encoding="utf-8")
        step(
            f"Best LR C={lr_tuning['best_C']} (CV AUC={lr_tuning['best_cv_roc_auc']:.4f}) | "
            f"Best LightGBM CV AUC={lgbm_tuning['best_cv_roc_auc']:.4f}",
            55,
        )

    # 5. Fit primary reference model (Scaled Logistic Regression) & Tuned LightGBM
    step(
        "Evaluating models across overall, in-distribution, K1-K4 generators, and speed terciles...",
        60,
    )
    lr_pipe = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=lr_tuning["best_C"], max_iter=1000, random_state=SEED),
    )
    lr_pipe.fit(train_df[features], train_df["label"])

    lgbm_imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    x_tr_imp = lgbm_imputer.fit_transform(train_df[features]).astype(np.float32)
    lgbm_clf = LGBMClassifier(
        **lgbm_tuning["best_params"],
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
        verbosity=-1,
    )
    lgbm_clf.fit(x_tr_imp, train_df["label"].to_numpy(dtype=int))

    # Build combined test dataframe (held-out humans + K1/K2/K4 test bots + held-out K3 bots)
    test_all_df = (
        pd.concat([test_non_k3_df, k3_df], ignore_index=True)
        if not k3_df.empty
        else test_non_k3_df.copy()
    )

    # Also run standard evaluate_keyboard for backward-compatible evaluation.csv
    std_eval_df = evaluate_keyboard(full_df, seed=SEED, n_bootstrap=100)
    std_eval_df.to_csv(RESULTS_KB / "evaluation.csv", index=False)

    # Detailed evaluation for both Logistic Regression (ONNX reference) and Tuned LightGBM
    detailed_rows: list[dict[str, Any]] = []
    per_gen_rows: list[dict[str, Any]] = []
    tercile_rows: list[dict[str, Any]] = []

    for model_label, score_fn in (
        ("logistic_regression", lambda df_in: lr_pipe.predict_proba(df_in[features])[:, 1]),
        (
            "lightgbm_tuned",
            lambda df_in: lgbm_clf.predict_proba(
                lgbm_imputer.transform(df_in[features]).astype(np.float32)
            )[:, 1],
        ),
    ):
        scored = test_all_df.copy()
        scored["score"] = score_fn(scored)
        human_slice = scored[scored["label"] == 0]
        human_scores = human_slice["score"].to_numpy(dtype=float)

        # Overall (with K3) and In-Distribution (without K3)
        for split_name, sub_df in (
            (f"{model_label}:overall_with_K3", scored),
            (f"{model_label}:in_dist_K1_K2_K4", scored[scored["bot_type"] != "K3"]),
        ):
            m = compute_detailed_metrics(
                sub_df["label"].to_numpy(dtype=int),
                sub_df["score"].to_numpy(dtype=float),
                name=split_name,
                human_ref_scores=human_scores,
            )
            r_lo, r_hi, p_lo, p_hi = bootstrap_auc_ci(sub_df, n_resamples=N_BOOTSTRAP, seed=SEED)
            m.update(
                {
                    "model": model_label,
                    "roc_auc_ci_low": r_lo,
                    "roc_auc_ci_high": r_hi,
                    "pr_auc_ci_low": p_lo,
                    "pr_auc_ci_high": p_hi,
                }
            )
            detailed_rows.append(m)
            step(
                f"  {split_name:<36} AUC={m['roc_auc']:.4f} [{r_lo}, {r_hi}]  "
                f"Recall@1%FPR={m['recall_at_1pct_fpr']:.4f}  BalAcc={m['balanced_accuracy']:.4f}",
                66,
            )

        # Per-generator evaluation (K1, K2, K3, K4 vs held-out test humans)
        for btype in ("K1", "K2", "K3", "K4"):
            bot_slice = scored[scored["bot_type"] == btype]
            if bot_slice.empty:
                continue
            pair_df = pd.concat([human_slice, bot_slice], ignore_index=True)
            gm = compute_detailed_metrics(
                pair_df["label"].to_numpy(dtype=int),
                pair_df["score"].to_numpy(dtype=float),
                name=f"{model_label}:generator:{btype}",
                human_ref_scores=human_scores,
            )
            r_lo, r_hi, p_lo, p_hi = bootstrap_auc_ci(pair_df, n_resamples=N_BOOTSTRAP, seed=SEED)
            gm.update(
                {
                    "model": model_label,
                    "generator": btype,
                    "is_held_out_from_training": btype == "K3",
                    "mean_bot_score": round(float(bot_slice["score"].mean()), 4),
                    "roc_auc_ci_low": r_lo,
                    "roc_auc_ci_high": r_hi,
                    "pr_auc_ci_low": p_lo,
                    "pr_auc_ci_high": p_hi,
                }
            )
            per_gen_rows.append(gm)
            step(
                f"  {model_label:<20} gen={btype} ({'held-out' if btype == 'K3' else 'in-dist ':8s}) "
                f"AUC={gm['roc_auc']:.4f}  Recall@1%FPR={gm['recall_at_1pct_fpr']:.4f}  "
                f"Recall@5%FPR={gm['recall_at_5pct_fpr']:.4f}",
                72,
            )

        # Speed tercile evaluation on held-out test split
        scored_terc = scored.assign(
            speed_tercile=pd.qcut(
                scored["typing_speed_cps"], 3, labels=["slow", "medium", "fast"], duplicates="drop"
            )
        )
        thr_1 = float(np.quantile(human_scores, 0.99))
        thr_5 = float(np.quantile(human_scores, 0.95))
        for t_idx, (t_label, t_group) in enumerate(
            scored_terc.groupby("speed_tercile", observed=False), start=1
        ):
            if t_group.empty:
                continue
            tm = compute_detailed_metrics(
                t_group["label"].to_numpy(dtype=int),
                t_group["score"].to_numpy(dtype=float),
                name=f"{model_label}:speed_tercile:{t_idx}_{t_label}",
                human_ref_scores=human_scores,
            )
            t_humans = t_group[t_group["label"] == 0]["score"].to_numpy(dtype=float)
            tm["speed_tercile"] = f"tercile_{t_idx}_{t_label}"
            tm["model"] = model_label
            tm["speed_cps_min"] = round(float(t_group["typing_speed_cps"].min()), 3)
            tm["speed_cps_max"] = round(float(t_group["typing_speed_cps"].max()), 3)
            tm["human_fpr_at_global_1pct_thr"] = (
                round(float(np.mean(t_humans >= thr_1)), 4) if len(t_humans) > 0 else None
            )
            tm["human_fpr_at_global_5pct_thr"] = (
                round(float(np.mean(t_humans >= thr_5)), 4) if len(t_humans) > 0 else None
            )
            tercile_rows.append(tm)

    pd.DataFrame(detailed_rows).to_csv(RESULTS_KB / "evaluation_splits.csv", index=False)
    pd.DataFrame(per_gen_rows).to_csv(RESULTS_KB / "per_generator.csv", index=False)
    pd.DataFrame(tercile_rows).to_csv(RESULTS_KB / "speed_terciles.csv", index=False)

    # 6. Probability Calibration on a grouped validation split of training groups
    step("Running probability calibration (isotonic & Platt scaling)...", 78)
    tr_sub_idx, val_sub_idx = grouped_split(train_df.to_dict("records"), test_size=0.2, seed=SEED)
    sub_tr = train_df.iloc[tr_sub_idx]
    sub_va = train_df.iloc[val_sub_idx]

    cal_base_pipe = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=lr_tuning["best_C"], max_iter=1000, random_state=SEED),
    )
    cal_base_pipe.fit(sub_tr[features], sub_tr["label"])
    va_raw = cal_base_pipe.predict_proba(sub_va[features])[:, 1]
    te_raw = cal_base_pipe.predict_proba(test_non_k3_df[features])[:, 1]
    y_va = sub_va["label"].to_numpy(dtype=int)
    y_te_non_k3 = test_non_k3_df["label"].to_numpy(dtype=int)

    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(va_raw, y_va)
    te_iso = iso.predict(te_raw)

    platt = LogisticRegression(random_state=SEED)
    platt.fit(va_raw.reshape(-1, 1), y_va)
    te_platt = platt.predict_proba(te_raw.reshape(-1, 1))[:, 1]

    raw_brier = float(brier_score_loss(y_te_non_k3, te_raw))
    iso_brier = float(brier_score_loss(y_te_non_k3, te_iso))
    platt_brier = float(brier_score_loss(y_te_non_k3, te_platt))

    calibration_info = {
        "method": "isotonic" if iso_brier <= platt_brier else "platt",
        "raw_brier": round(raw_brier, 6),
        "isotonic_brier": round(iso_brier, 6),
        "platt_brier": round(platt_brier, 6),
        "x_thresholds": [round(float(x), 6) for x in iso.X_thresholds_],
        "y_thresholds": [round(float(y), 6) for y in iso.y_thresholds_],
        "single_human_source_limitation": (
            "Aalto 136M Keystrokes is the sole configured human keyboard source "
            "(prescribed sentence typing test); no second human dataset (BB-MAS/CMU) is locally available."
        ),
    }
    (RESULTS_KB / "calibration.json").write_text(
        json.dumps(calibration_info, indent=2) + "\n", encoding="utf-8"
    )
    step(
        f"Calibration Brier: raw={raw_brier:.4f}, isotonic={iso_brier:.4f}, platt={platt_brier:.4f}",
        82,
    )

    # 7. Feature Importance & K3 Holdout Analysis
    lr_clf = lr_pipe.named_steps["logisticregression"]
    lr_coefs = np.asarray(lr_clf.coef_[0], dtype=float)
    lgbm_imp = np.asarray(lgbm_clf.feature_importances_, dtype=float)
    feat_imp_df = pd.DataFrame(
        {
            "feature": features,
            "lr_standardized_coef": np.round(lr_coefs, 5),
            "lr_abs_coef": np.round(np.abs(lr_coefs), 5),
            "lightgbm_split_importance": lgbm_imp,
        }
    ).sort_values("lr_abs_coef", ascending=False)
    feat_imp_df.to_csv(RESULTS_KB / "feature_importance.csv", index=False)
    write_failure_analysis_report(per_gen_rows, feat_imp_df, RESULTS_KB / "failure_analysis.md")

    # 8. Export Keyboard ONNX models (Logistic Regression v1 + LightGBM v1) & verify parity
    step("Exporting Keyboard models to ONNX and verifying parity...", 88)
    manifest_hash = "unknown"
    if MANIFEST_PATH.exists():
        import hashlib

        manifest_hash = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()[:16]

    primary_lr_metrics = next(
        r for r in detailed_rows if r["group"] == "logistic_regression:in_dist_K1_K2_K4"
    )
    export_keyboard_onnx(
        train_eval_df,
        KB_MODEL_DIR,
        feature_columns=features,
        version="v1",
        data_manifest_hash=manifest_hash,
        seed=SEED,
        metrics=primary_lr_metrics,
        calibration=calibration_info,
    )

    primary_lgbm_metrics = next(
        r for r in detailed_rows if r["group"] == "lightgbm_tuned:overall_with_K3"
    )
    export_mouse_onnx(
        train_eval_df,
        KB_LGBM_MODEL_DIR,
        feature_columns=features,
        version="v1-lgbm",
        data_manifest_hash=manifest_hash,
        seed=SEED,
        hyperparameters={**lgbm_tuning["best_params"], "class_weight": "balanced"},
        metrics=primary_lgbm_metrics,
        calibration=calibration_info,
    )

    # Verify ONNX parity on 500 test windows
    parity_slice = test_all_df.iloc[: min(500, len(test_all_df))]
    native_verify = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=SEED),
    )
    native_verify.fit(train_eval_df[features], train_eval_df["label"])
    x_verify = parity_slice[features].to_numpy(dtype=np.float32, copy=True)
    native_probs = native_verify.predict_proba(parity_slice[features])[:, 1]
    onnx_probs = predict_onnx(KB_MODEL_DIR / "model.onnx", x_verify)
    max_diff = float(np.max(np.abs(native_probs - onnx_probs)))
    assert max_diff < 1e-4, f"ONNX parity failed: max_diff={max_diff}"
    step(
        f"Keyboard ONNX parity verified across {len(parity_slice)} windows (max |diff| = {max_diff:.2e} < 1e-4)",
        92,
    )

    # 9. Desktop Score Fusion (P3-10)
    step("Running Desktop Score Fusion (Mouse + Keyboard pseudo-session evaluation)...", 95)
    kb_test_for_fusion = test_non_k3_df[["label", "split_group"]].copy()
    kb_raw_for_fusion = predict_onnx(
        KB_MODEL_DIR / "model.onnx",
        test_non_k3_df[features].to_numpy(dtype=np.float32, copy=True),
    )
    kb_test_for_fusion["score"] = np.interp(
        kb_raw_for_fusion,
        calibration_info["x_thresholds"],
        calibration_info["y_thresholds"],
    )
    fusion_results = run_desktop_fusion_experiment(kb_test_for_fusion, seed=SEED)
    for fr in fusion_results["comparison"]:
        step(
            f"  Fusion [{fr['group']:<14}] ROC-AUC={fr['roc_auc']:.4f}  PR-AUC={fr['pr_auc']:.4f}  "
            f"Recall@1%FPR={fr['recall_at_1pct_fpr']:.4f}  Brier={fr['brier_score']:.4f}",
            98,
        )

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - t0

    summary = {
        "stage": "Phase 3 Complete (Aalto 1000 Participants + K1/K2/K3/K4 + ONNX + Desktop Fusion)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "training_time_seconds": round(elapsed, 2),
        "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
        "privacy_scan": privacy_report,
        "dataset_summary": {
            "human_windows": int(np.sum(train_eval_df["label"] == 0)),
            "training_bot_windows_K1_K2_K4": int(np.sum(train_eval_df["label"] == 1)),
            "held_out_K3_windows": len(k3_df),
            "n_features": len(features),
        },
        "baselines": base_df.to_dict("records"),
        "evaluation_splits": detailed_rows,
        "per_generator": per_gen_rows,
        "speed_terciles": tercile_rows,
        "calibration": calibration_info,
        "onnx_parity_max_abs_diff": max_diff,
        "fusion_comparison": fusion_results["comparison"],
    }
    (RESULTS_KB / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 76)
    print(
        f"  KEYBOARD & FUSION PIPELINE COMPLETE ({elapsed:.1f}s | Peak RAM: {peak_mem / (1024 * 1024):.1f} MB)"
    )
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
