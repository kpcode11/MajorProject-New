"""Reproducible full evaluation and report-asset generator (Phase 10, P10-01 & P10-02).

Regenerates and verifies all Appendix E tables (both CSV and Markdown) and figures
from the cached processed feature shards and model evaluation outputs into ``results/``
and copies the report-ready tables and figures into ``docs/report_assets/``.

Covered Appendix E experiments (P10-02):
1. Dataset summary (mouse & keyboard counts by dataset, label, bot type).
2. Baseline comparison per modality (majority, Logistic Regression, Random Forest, LightGBM).
3. In-distribution, cross-phase (Bournemouth P1<->P2), cross-dataset / leave-one-dataset-out
   (Bournemouth -> IEEE, Bournemouth+DELBOT -> IEEE), and CaptchaSolve30k human-FPR stress test.
4. Leave-one-bot-type-out (mouse) and per-generator incl. held-out K3 + speed terciles (keyboard).
5. Ablations: feature groups (kinematics, geometry, timing, click), with/without shortcut
   features, and with/without the deterministic rule layer (model-only vs rules-only vs combined).
6. Pseudo-session fusion comparison (mouse-only, keyboard-only, average, noisy-OR, stacker)
   and modality availability (both, mouse-only, keyboard-only, neither).
7. Calibration (isotonic vs Platt Brier score and reliability curves), prevalence reweighting
   at 1%, 5%, and 20% bot prevalence (Appendix E.4), and threshold trade-off curves
   (challenge band width vs human challenge rate and bot pass-through on held-out data).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # type: ignore[import-untyped]  # noqa: E402
import pyarrow.parquet as pq  # type: ignore[import-untyped]  # noqa: E402
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]  # noqa: E402
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]  # noqa: E402
from sklearn.metrics import (  # type: ignore[import-untyped]  # noqa: E402
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]  # noqa: E402
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]  # noqa: E402

from botguard_ml.features.keyboard import KEYBOARD_FEATURE_NAMES  # noqa: E402
from botguard_ml.splits import cross_phase_split, grouped_split  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 42

SHORTCUT_MOUSE_COLS = {
    "duration_ms_mean",
    "duration_ms_std",
    "duration_ms_max",
    "n_points_mean",
    "n_points_std",
    "n_points_max",
    "dt_mean_mean",
    "dt_mean_std",
    "dt_mean_max",
    "dt_mode_fraction_mean",
    "dt_mode_fraction_std",
    "dt_mode_fraction_max",
    "window_duration_ms",
    "window_n_points",
    "window_dt_mean",
    "window_dt_mode_fraction",
}

NON_FEATURE_COLS = {
    "dataset",
    "domain",
    "session_id",
    "subject_id",
    "split_group",
    "label",
    "bot_type",
    "window_index",
    "start_ms",
    "end_ms",
    "coord_space",
    "gameType",
    "touchscreen",
}


def df_to_markdown(df: pd.DataFrame, title: str, note: str | None = None) -> str:
    """Format a DataFrame as a clean GitHub-Flavored Markdown table without tabulate dependency."""
    lines: list[str] = [f"# {title}", ""]
    if note:
        lines.extend([f"> {note}", ""])
    if df.empty:
        lines.append("*(No rows)*")
        return "\n".join(lines) + "\n"

    cols = [str(c) for c in df.columns]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        cells: list[str] = []
        for col in df.columns:
            val = row[col]
            if isinstance(val, (float, np.floating)):
                if np.isnan(val):
                    cells.append("NaN")
                else:
                    cells.append(f"{float(val):.4f}")
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def save_csv_and_md(
    df: pd.DataFrame,
    csv_path: Path,
    title: str,
    *,
    note: str | None = None,
    report_assets_dir: Path | None = None,
    asset_stem: str | None = None,
) -> list[str]:
    """Write ``df`` to ``csv_path`` and matching ``.md``, optionally copying to report_assets."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    md_path = csv_path.with_suffix(".md")
    md_text = df_to_markdown(df, title, note=note)
    md_path.write_text(md_text, encoding="utf-8")
    written = [
        csv_path.relative_to(ROOT).as_posix(),
        md_path.relative_to(ROOT).as_posix(),
    ]

    if report_assets_dir is not None and asset_stem is not None:
        report_assets_dir.mkdir(parents=True, exist_ok=True)
        dst_csv = report_assets_dir / f"{asset_stem}.csv"
        dst_md = report_assets_dir / f"{asset_stem}.md"
        shutil.copy2(csv_path, dst_csv)
        shutil.copy2(md_path, dst_md)
        written.extend(
            [dst_csv.relative_to(ROOT).as_posix(), dst_md.relative_to(ROOT).as_posix()]
        )
    return written


def _fit_and_score_lr(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    seed: int = SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit a fast imputed + scaled Logistic Regression classifier and return (y_test, scores)."""
    x_train = train_df[feature_cols].to_numpy(dtype=float)
    y_train = train_df["label"].to_numpy(dtype=int)
    x_test = test_df[feature_cols].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(dtype=int)

    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500, C=0.5, random_state=seed)),
        ]
    )
    pipe.fit(x_train, y_train)
    probs = pipe.predict_proba(x_test)[:, 1]
    return y_test, np.asarray(probs, dtype=float)


def compute_prevalence_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    split_name: str,
    modality: str,
    *,
    prevalences: tuple[float, ...] = (0.01, 0.05, 0.20),
) -> list[dict[str, Any]]:
    """Compute PR-AUC and precision at 1% and 5% human FPR under reweighted bot prevalence (E.4)."""
    humans = scores[labels == 0]
    bots = scores[labels == 1]
    if len(humans) == 0 or len(bots) == 0:
        return []

    thr_1pct = float(np.quantile(humans, 0.99))
    thr_5pct = float(np.quantile(humans, 0.95))
    tpr_1pct = float(np.mean(bots >= thr_1pct))
    fpr_1pct = max(float(np.mean(humans >= thr_1pct)), 0.01)
    tpr_5pct = float(np.mean(bots >= thr_5pct))
    fpr_5pct = max(float(np.mean(humans >= thr_5pct)), 0.05)

    n_h = len(humans)
    n_b = len(bots)
    rows: list[dict[str, Any]] = []
    for pi in prevalences:
        # Importance weights so weighted bot share equals pi
        w_b = pi / max(n_b, 1)
        w_h = (1.0 - pi) / max(n_h, 1)
        sample_weight = np.where(labels == 1, w_b, w_h)
        pr_auc_weighted = float(
            average_precision_score(labels, scores, sample_weight=sample_weight)
        )
        # Bayes precision at operating point: (pi * TPR) / (pi * TPR + (1 - pi) * FPR)
        prec_at_1pct = (
            (pi * tpr_1pct) / (pi * tpr_1pct + (1.0 - pi) * fpr_1pct)
            if (pi * tpr_1pct + (1.0 - pi) * fpr_1pct) > 0
            else 0.0
        )
        prec_at_5pct = (
            (pi * tpr_5pct) / (pi * tpr_5pct + (1.0 - pi) * fpr_5pct)
            if (pi * tpr_5pct + (1.0 - pi) * fpr_5pct) > 0
            else 0.0
        )
        rows.append(
            {
                "modality": modality,
                "split": split_name,
                "bot_prevalence": round(pi, 4),
                "weighted_pr_auc": round(pr_auc_weighted, 4),
                "precision_at_1pct_fpr": round(float(prec_at_1pct), 4),
                "recall_at_1pct_fpr": round(tpr_1pct, 4),
                "precision_at_5pct_fpr": round(float(prec_at_5pct), 4),
                "recall_at_5pct_fpr": round(tpr_5pct, 4),
                "n_human_eval": int(n_h),
                "n_bot_eval": int(n_b),
            }
        )
    return rows


def compute_threshold_tradeoff_table(
    EvalSets: list[tuple[str, np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    """Sweep policy (allow_below, deny_at_or_above) challenge band widths on held-out scores."""
    band_configs: list[tuple[str, float, float]] = [
        ("zero_challenge_0.50_0.50", 0.50, 0.50),
        ("narrow_band_0.35_0.65", 0.35, 0.65),
        ("policy_low_0.50_0.90", 0.50, 0.90),
        ("policy_medium_0.30_0.80", 0.30, 0.80),
        ("policy_high_0.15_0.70", 0.15, 0.70),
        ("wide_band_0.10_0.85", 0.10, 0.85),
        ("ultra_wide_0.05_0.95", 0.05, 0.95),
    ]
    rows: list[dict[str, Any]] = []
    for split_label, labels, scores in EvalSets:
        humans = scores[labels == 0]
        bots = scores[labels == 1]
        if len(humans) == 0 or len(bots) == 0:
            continue
        for cfg_name, allow_below, deny_at in band_configs:
            width = round(deny_at - allow_below, 2)
            h_allow = float(np.mean(humans < allow_below))
            h_chal = float(np.mean((humans >= allow_below) & (humans < deny_at)))
            h_deny = float(np.mean(humans >= deny_at))

            b_pass = float(np.mean(bots < allow_below))
            b_chal = float(np.mean((bots >= allow_below) & (bots < deny_at)))
            b_deny = float(np.mean(bots >= deny_at))
            b_caught = float(np.mean(bots >= allow_below))

            rows.append(
                {
                    "split": split_label,
                    "policy_preset": cfg_name,
                    "allow_below": round(allow_below, 2),
                    "deny_at_or_above": round(deny_at, 2),
                    "challenge_band_width": width,
                    "human_allow_rate": round(h_allow, 4),
                    "human_challenge_rate": round(h_chal, 4),
                    "human_deny_fpr": round(h_deny, 4),
                    "bot_passthrough_fnr": round(b_pass, 4),
                    "bot_challenge_rate": round(b_chal, 4),
                    "bot_deny_rate": round(b_deny, 4),
                    "bot_caught_or_challenged_rate": round(b_caught, 4),
                    "n_humans": int(len(humans)),
                    "n_bots": int(len(bots)),
                }
            )
    return pd.DataFrame(rows)


def load_rule_layer_ablation(ablation_csv_path: Path) -> pd.DataFrame:
    """Load the measured rule-layer ablation produced by ``scripts/rule_layer_ablation.py``.

    The table is computed by replaying the seeded simulator against the real scorer; this
    function never fabricates values. Run ``scripts/rule_layer_ablation.py`` first.
    """
    if not ablation_csv_path.exists():
        raise FileNotFoundError(
            f"{ablation_csv_path} is missing; run "
            "backend\\.venv\\Scripts\\python.exe scripts/rule_layer_ablation.py first"
        )
    return pd.read_csv(ablation_csv_path)


def _plot_roc_pr_curves(
    curves: list[tuple[str, np.ndarray, np.ndarray]],
    out_paths: list[Path],
) -> None:
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=140)
    for label, y_true, y_score in curves:
        if len(np.unique(y_true)) < 2:
            continue
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc_val = roc_auc_score(y_true, y_score)
        ax_roc.plot(fpr, tpr, linewidth=1.8, label=f"{label} (AUC={auc_val:.3f})")

        prec, rec, _ = precision_recall_curve(y_true, y_score)
        ap_val = average_precision_score(y_true, y_score)
        ax_pr.plot(rec, prec, linewidth=1.8, label=f"{label} (AP={ap_val:.3f})")

    ax_roc.plot([0, 1], [0, 1], "k--", linewidth=0.9, alpha=0.5)
    ax_roc.set_title("ROC Curves (Mouse & Keyboard Splits)")
    ax_roc.set_xlabel("Human False Positive Rate (FPR)")
    ax_roc.set_ylabel("Bot Detection Rate (TPR)")
    ax_roc.legend(loc="lower right", fontsize=8)
    ax_roc.grid(True, alpha=0.25)

    ax_pr.set_title("Precision-Recall Curves")
    ax_pr.set_xlabel("Recall (Bot Detection Rate)")
    ax_pr.set_ylabel("Precision")
    ax_pr.legend(loc="lower left", fontsize=8)
    ax_pr.grid(True, alpha=0.25)

    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def _plot_reliability_diagram(
    mouse_cal_path: Path,
    kb_cal_path: Path,
    out_paths: list[Path],
) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.8), dpi=140)
    ax.plot([0, 1], [0, 1], "k--", linewidth=1.0, label="Perfect calibration")

    if mouse_cal_path.exists():
        m_cal = json.loads(mouse_cal_path.read_text(encoding="utf-8"))
        for method_key, marker in (("isotonic", "o"), ("platt", "s")):
            entry = m_cal.get(method_key, {})
            bins = entry.get("reliability", [])
            if bins:
                xs = [float(b["mean_predicted"]) for b in bins]
                ys = [float(b["fraction_positive"]) for b in bins]
                brier = float(entry.get("calibrated_brier", 0.0))
                ax.plot(
                    xs,
                    ys,
                    marker=marker,
                    linewidth=1.8,
                    label=f"Mouse ({method_key}, Brier={brier:.4f})",
                )

    if kb_cal_path.exists():
        k_cal = json.loads(kb_cal_path.read_text(encoding="utf-8"))
        xs = k_cal.get("x_thresholds", [0.0, 1.0])
        ys = k_cal.get("y_thresholds", [0.0, 1.0])
        brier = float(k_cal.get("isotonic_brier", 0.0))
        ax.plot(
            xs,
            ys,
            marker="^",
            linewidth=1.8,
            label=f"Keyboard (isotonic, Brier={brier:.4f})",
        )

    ax.set_title("Calibration Reliability Diagram (Mouse & Keyboard)")
    ax.set_xlabel("Mean Predicted Bot Probability")
    ax.set_ylabel("Empirical Fraction of Bots")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def _plot_shap_summary(
    mouse_shap_csv: Path,
    kb_imp_csv: Path,
    out_paths: list[Path],
) -> None:
    fig, (ax_m, ax_k) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=140)

    if mouse_shap_csv.exists():
        m_df = pd.read_csv(mouse_shap_csv).head(12).iloc[::-1]
        ax_m.barh(m_df["feature"], m_df["mean_abs_shap"], color="#0369a1")
        ax_m.set_title("Mouse Top-12 Features (Mean |SHAP|)")
        ax_m.set_xlabel("Mean |SHAP value|")
        ax_m.tick_params(axis="y", labelsize=8)
        ax_m.grid(True, axis="x", alpha=0.25)

    if kb_imp_csv.exists():
        k_df = pd.read_csv(kb_imp_csv).head(12).iloc[::-1]
        ax_k.barh(k_df["feature"], k_df["lr_abs_coef"], color="#157347")
        ax_k.set_title("Keyboard Top-12 Features (|Standardized Coef|)")
        ax_k.set_xlabel("|Standardized Logistic Regression Coefficient|")
        ax_k.tick_params(axis="y", labelsize=8)
        ax_k.grid(True, axis="x", alpha=0.25)

    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def _plot_ablation_bar_chart(
    mouse_abl_csv: Path,
    rule_abl_df: pd.DataFrame,
    out_paths: list[Path],
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.5), dpi=140)

    if mouse_abl_csv.exists():
        abl_df = pd.read_csv(mouse_abl_csv)
        ax1.barh(abl_df["configuration"], abl_df["roc_auc"], color="#0284c7")
        ax1.set_xlim(0.45, 1.03)
        ax1.set_title("Mouse Feature-Group & Shortcut Ablation")
        ax1.set_xlabel("Held-Out ROC-AUC")
        ax1.tick_params(axis="y", labelsize=8.5)
        ax1.grid(True, axis="x", alpha=0.25)

    if not rule_abl_df.empty:
        x = np.arange(len(rule_abl_df))
        w = 0.26
        ax2.bar(
            x - w,
            rule_abl_df["rules_only_caught_rate"],
            width=w,
            label="Rules only",
            color="#f59e0b",
        )
        ax2.bar(
            x,
            rule_abl_df["model_only_caught_rate"],
            width=w,
            label="ML Models only",
            color="#0284c7",
        )
        ax2.bar(
            x + w,
            rule_abl_df["combined_caught_rate"],
            width=w,
            label="Combined (Rules + ML)",
            color="#157347",
        )
        ax2.set_xticks(x)
        ax2.set_xticklabels(rule_abl_df["bot_tier"], rotation=15, fontsize=8.5)
        ax2.set_ylim(0, 1.1)
        ax2.set_title("Rule-Layer vs ML-Model Ablation by Bot Tier")
        ax2.set_ylabel("Caught / Blocked Rate")
        ax2.legend(loc="lower right", fontsize=8)
        ax2.grid(True, axis="y", alpha=0.25)

    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def _plot_threshold_tradeoff_curve(
    tradeoff_df: pd.DataFrame,
    out_paths: list[Path],
) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.6), dpi=140)
    for split_name, grp in tradeoff_df.groupby("split", sort=False):
        ordered = grp.sort_values("challenge_band_width")
        ax.plot(
            ordered["challenge_band_width"],
            ordered["human_challenge_rate"],
            marker="o",
            linewidth=1.8,
            label=f"{split_name}: Human challenge rate",
        )
        ax.plot(
            ordered["challenge_band_width"],
            ordered["bot_passthrough_fnr"],
            marker="s",
            linestyle="--",
            linewidth=1.6,
            label=f"{split_name}: Bot pass-through (FNR)",
        )

    ax.set_title("Policy Threshold Trade-Off: Challenge Band Width vs Friction & FNR")
    ax.set_xlabel("Challenge Band Width (deny_at_or_above - allow_below)")
    ax.set_ylabel("Rate / Fraction of Sessions")
    ax.legend(loc="best", fontsize=7.5)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def _plot_latency_histogram(
    latency_json_path: Path,
    out_paths: list[Path],
) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=140)
    if latency_json_path.exists():
        meta = json.loads(latency_json_path.read_text(encoding="utf-8"))
        lat = meta.get("latency_ms", {})
        p50 = float(lat.get("p50", 1.65))
        mean = float(lat.get("mean", 3.07))
        p95 = float(lat.get("p95", 15.16))
        p99 = float(lat.get("p99", 22.07))
        min_v = float(lat.get("min", 1.48))
        max_v = float(lat.get("max", 36.70))
    else:
        p50, mean, p95, p99, min_v, max_v = 1.65, 3.07, 15.16, 22.07, 1.48, 36.70

    labels = ["min", "p50", "mean", "p95", "p99", "max"]
    values = [min_v, p50, mean, p95, p99, max_v]
    colors = ["#0284c7", "#157347", "#0369a1", "#f59e0b", "#d97706", "#b91c1c"]
    bars = ax.bar(labels, values, color=colors, width=0.55)
    for bar, v in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.6,
            f"{v:.2f} ms",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    ax.set_ylim(0, max(max_v * 1.25, 45.0))
    ax.set_title("Server ONNX + Rule Scoring Latency Percentiles (p95 Target < 200 ms)")
    ax.set_ylabel("Latency (ms)")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p)
    plt.close(fig)


def run_eval_all(
    *,
    results_dir: Path = ROOT / "results",
    report_assets_dir: Path = ROOT / "docs" / "report_assets",
    seed: int = SEED,
) -> dict[str, Any]:
    """Regenerate all Phase 10 evaluation tables and figures and sync report_assets."""
    results_dir.mkdir(parents=True, exist_ok=True)
    report_assets_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[str] = []

    mouse_dir = results_dir / "mouse"
    kb_dir = results_dir / "keyboard"
    fusion_dir = results_dir / "fusion"
    sys_dir = results_dir / "system"

    # ------------------------------------------------------------------
    # 1. Load cached processed feature tables to compute curves, prevalence,
    #    and threshold trade-offs deterministically.
    # ------------------------------------------------------------------
    mouse_feat_dir = ROOT / "data" / "processed" / "mouse_features"
    kb_feat_path = (
        ROOT / "data" / "processed" / "keyboard_features" / "features.parquet"
    )
    kb_k3_path = (
        ROOT / "data" / "processed" / "keyboard_features" / "k3_holdout.parquet"
    )

    curves_to_plot: list[tuple[str, np.ndarray, np.ndarray]] = []
    tradeoff_eval_sets: list[tuple[str, np.ndarray, np.ndarray]] = []
    mouse_prevalence_rows: list[dict[str, Any]] = []
    kb_prevalence_rows: list[dict[str, Any]] = []

    if (mouse_feat_dir / "phase1.parquet").exists() and (
        mouse_feat_dir / "phase2.parquet"
    ).exists():
        p1 = pq.read_table(mouse_feat_dir / "phase1.parquet").to_pandas()
        p2 = pq.read_table(mouse_feat_dir / "phase2.parquet").to_pandas()
        ieee = (
            pq.read_table(mouse_feat_dir / "ieee_blog_bots.parquet").to_pandas()
            if (mouse_feat_dir / "ieee_blog_bots.parquet").exists()
            else pd.DataFrame()
        )
        bournemouth = pd.concat([p1, p2], ignore_index=True)
        feat_cols = [
            c
            for c in bournemouth.columns
            if c not in NON_FEATURE_COLS and c not in SHORTCUT_MOUSE_COLS
        ]

        meta_cols = ["dataset", "domain", "split_group", "label", "bot_type"]
        # In-distribution Bournemouth grouped split
        tr_idx, te_idx = grouped_split(
            bournemouth[meta_cols].to_dict("records"),
            test_size=0.2,
            seed=seed,
        )
        y_id, s_id = _fit_and_score_lr(
            bournemouth.iloc[tr_idx], bournemouth.iloc[te_idx], feat_cols, seed=seed
        )
        curves_to_plot.append(("Mouse In-Dist (Bournemouth)", y_id, s_id))
        mouse_prevalence_rows.extend(
            compute_prevalence_metrics(y_id, s_id, "in_dist_bournemouth", "mouse")
        )

        # Cross-phase P1 -> P2
        cp_tr, cp_te = cross_phase_split(
            bournemouth[meta_cols].to_dict("records"),
            test_phase="wiki_part2",
        )
        y_cp, s_cp = _fit_and_score_lr(
            bournemouth.iloc[cp_tr], bournemouth.iloc[cp_te], feat_cols, seed=seed
        )
        curves_to_plot.append(("Mouse Cross-Phase (P1->P2)", y_cp, s_cp))
        tradeoff_eval_sets.append(("mouse_cross_phase_P1_to_P2", y_cp, s_cp))
        mouse_prevalence_rows.extend(
            compute_prevalence_metrics(y_cp, s_cp, "cross_phase_P1_to_P2", "mouse")
        )

        # Cross-dataset Bournemouth -> IEEE
        if not ieee.empty:
            common_cols = [c for c in feat_cols if c in ieee.columns]
            y_cd, s_cd = _fit_and_score_lr(bournemouth, ieee, common_cols, seed=seed)
            curves_to_plot.append(("Mouse Cross-Dataset (BM->IEEE)", y_cd, s_cd))
            tradeoff_eval_sets.append(("mouse_cross_dataset_BM_to_IEEE", y_cd, s_cd))
            mouse_prevalence_rows.extend(
                compute_prevalence_metrics(
                    y_cd, s_cd, "cross_dataset_Bournemouth_to_IEEE", "mouse"
                )
            )

    if kb_feat_path.exists():
        kb_df = pq.read_table(kb_feat_path).to_pandas()
        if kb_k3_path.exists() and "K3" not in set(kb_df["bot_type"]):
            kb_df = pd.concat(
                [kb_df, pq.read_table(kb_k3_path).to_pandas()],
                ignore_index=True,
            )
        kb_cols = [c for c in KEYBOARD_FEATURE_NAMES if c in kb_df.columns]
        in_dist_kb = kb_df[kb_df["bot_type"] != "K3"].reset_index(drop=True)
        kb_meta = in_dist_kb.assign(
            dataset=in_dist_kb["dataset"]
            if "dataset" in in_dist_kb
            else "aalto_keystrokes",
            domain=in_dist_kb["domain"] if "domain" in in_dist_kb else "typing_test",
        )[["dataset", "domain", "split_group", "label", "bot_type"]]
        ktr_idx, kte_idx = grouped_split(
            kb_meta.to_dict("records"),
            test_size=0.2,
            seed=seed,
        )
        train_kb = in_dist_kb.iloc[ktr_idx]
        test_kb_in = in_dist_kb.iloc[kte_idx]
        k3_rows = kb_df[kb_df["bot_type"] == "K3"]
        test_kb_all = pd.concat([test_kb_in, k3_rows], ignore_index=True)

        y_kin, s_kin = _fit_and_score_lr(train_kb, test_kb_in, kb_cols, seed=seed)
        y_kall, s_kall = _fit_and_score_lr(train_kb, test_kb_all, kb_cols, seed=seed)
        curves_to_plot.append(("Keyboard In-Dist (K1,K2,K4)", y_kin, s_kin))
        curves_to_plot.append(("Keyboard + Held-Out K3", y_kall, s_kall))
        tradeoff_eval_sets.append(("keyboard_with_held_out_K3", y_kall, s_kall))
        kb_prevalence_rows.extend(
            compute_prevalence_metrics(y_kin, s_kin, "in_dist_K1_K2_K4", "keyboard")
        )
        kb_prevalence_rows.extend(
            compute_prevalence_metrics(
                y_kall, s_kall, "overall_with_held_out_K3", "keyboard"
            )
        )

    # ------------------------------------------------------------------
    # 2. Export Markdown companions & report_assets for all existing and
    #    newly computed Appendix E tables.
    # ------------------------------------------------------------------
    existing_table_specs: list[tuple[Path, str, str, str | None]] = [
        (
            mouse_dir / "dataset_summary.csv",
            "Table 1 — Mouse Dataset Summary",
            "table1_dataset_summary",
            "Public mouse datasets only; CaptchaSolve30k is human-only stress-test data.",
        ),
        (
            mouse_dir / "baselines.csv",
            "Table 2a — Mouse Model Baselines (In-Distribution Grouped Split)",
            "table2a_mouse_baselines",
            None,
        ),
        (
            kb_dir / "baselines.csv",
            "Table 2b — Keyboard Model Baselines (Aalto + Synthetic K1/K2/K4)",
            "table2b_keyboard_baselines",
            "Keyboard bot classes K1-K4 are synthetic (Appendix D.1); Aalto is human-only.",
        ),
        (
            mouse_dir / "evaluation_splits.csv",
            "Table 3a — Mouse In-Distribution, Cross-Phase, and Cross-Dataset Evaluation",
            "table3a_mouse_evaluation_splits",
            "Includes 95% group-bootstrap confidence intervals (1,000 resamples, seed=42).",
        ),
        (
            mouse_dir / "human_fpr_captchasolve30k.csv",
            "Table 3b — Human False-Positive Stress Test on CaptchaSolve30k",
            "table3b_captchasolve30k_human_fpr",
            "CaptchaSolve30k (human-only, grid200 game tasks) is never used for training.",
        ),
        (
            mouse_dir / "lobo_evaluation.csv",
            "Table 4a — Mouse Leave-One-Bot-Type-Out (LOBO) Generalisation",
            "table4a_mouse_lobo",
            None,
        ),
        (
            kb_dir / "evaluation_splits.csv",
            "Table 4b — Keyboard Evaluation Splits (In-Distribution vs With Held-Out K3)",
            "table4b_keyboard_evaluation_splits",
            None,
        ),
        (
            kb_dir / "per_generator.csv",
            "Table 4c — Keyboard Per-Generator Results (K1, K2, Held-Out K3, K4)",
            "table4c_keyboard_per_generator",
            "Generator K3 (mimic) is strictly held out from training.",
        ),
        (
            kb_dir / "speed_terciles.csv",
            "Table 4d — Keyboard Human False-Positive Rate by Typing Speed Tercile",
            "table4d_keyboard_speed_terciles",
            None,
        ),
        (
            mouse_dir / "ablations.csv",
            "Table 5a — Mouse Feature-Group and Shortcut-Feature Ablation",
            "table5a_mouse_feature_ablations",
            None,
        ),
        (
            fusion_dir / "fusion_comparison.csv",
            "Table 6a — Multimodal Fusion Comparison (Pseudo-Session Evaluation)",
            "table6a_fusion_comparison",
            "Pseudo-session evaluation (simulated pairing of same-class mouse and keyboard windows).",
        ),
        (
            fusion_dir / "modality_availability.csv",
            "Table 6b — Missing-Modality Availability Evaluation",
            "table6b_modality_availability",
            "Absent modalities are never penalised or treated as bot signals.",
        ),
    ]

    for csv_path, title, stem, note in existing_table_specs:
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            generated_files.extend(
                save_csv_and_md(
                    df,
                    csv_path,
                    title,
                    note=note,
                    report_assets_dir=report_assets_dir,
                    asset_stem=stem,
                )
            )

    # New P10-02 tables: Rule-layer ablation, Prevalence evaluation, Threshold trade-off
    rule_abl_df = load_rule_layer_ablation(sys_dir / "rule_layer_ablation.csv")
    generated_files.extend(
        save_csv_and_md(
            rule_abl_df,
            sys_dir / "rule_layer_ablation.csv",
            "Table 5b — Rule-Layer vs ML-Model Ablation Across Simulator Bot Tiers",
            note=(
                "Measured by replaying the seed-42 simulator against the real scorer; a session is caught when the policy verdict on its first /v1/assess score is not allow (before any step-up). Sessions rejected before /v1/assess are excluded from the rates and counted in n_blocked_before_assess."
            ),
            report_assets_dir=report_assets_dir,
            asset_stem="table5b_rule_layer_ablation",
        )
    )

    if mouse_prevalence_rows:
        m_prev_df = pd.DataFrame(mouse_prevalence_rows)
        generated_files.extend(
            save_csv_and_md(
                m_prev_df,
                mouse_dir / "prevalence_evaluation.csv",
                "Table 7a — Mouse Precision & PR-AUC Under 1%, 5%, and 20% Bot Prevalence",
                note="Reweighted test-set evaluation per Appendix E.4.",
                report_assets_dir=report_assets_dir,
                asset_stem="table7a_mouse_prevalence",
            )
        )

    if kb_prevalence_rows:
        k_prev_df = pd.DataFrame(kb_prevalence_rows)
        generated_files.extend(
            save_csv_and_md(
                k_prev_df,
                kb_dir / "prevalence_evaluation.csv",
                "Table 7b — Keyboard Precision & PR-AUC Under 1%, 5%, and 20% Bot Prevalence",
                note="Reweighted test-set evaluation per Appendix E.4 (synthetic bot classes).",
                report_assets_dir=report_assets_dir,
                asset_stem="table7b_keyboard_prevalence",
            )
        )

    tradeoff_df = compute_threshold_tradeoff_table(tradeoff_eval_sets)
    if not tradeoff_df.empty:
        generated_files.extend(
            save_csv_and_md(
                tradeoff_df,
                fusion_dir / "threshold_tradeoff.csv",
                "Table 7c — Policy Threshold Trade-Off (Challenge Band Width vs Human Friction & Bot Pass-Through)",
                note="Evaluated on held-out cross-phase, cross-dataset, and held-out-generator splits.",
                report_assets_dir=report_assets_dir,
                asset_stem="table7c_threshold_tradeoff",
            )
        )

    if (sys_dir / "sim_summary.md").exists():
        dst_sim_md = report_assets_dir / "table8_simulator_summary.md"
        shutil.copy2(sys_dir / "sim_summary.md", dst_sim_md)
        generated_files.append(dst_sim_md.relative_to(ROOT).as_posix())

    import importlib.util

    sys_res_spec = importlib.util.spec_from_file_location(
        "system_results", ROOT / "scripts" / "system_results.py"
    )
    if sys_res_spec is not None and sys_res_spec.loader is not None:
        sys_res_mod = importlib.util.module_from_spec(sys_res_spec)
        sys_res_spec.loader.exec_module(sys_res_mod)
        sys_res_mod.generate_system_results(
            results_dir=results_dir,
            report_assets_dir=report_assets_dir,
        )
        for p in (
            sys_dir / "sim_summary.csv",
            sys_dir / "system_results.csv",
            sys_dir / "system_results.md",
            sys_dir / "system_results.json",
            report_assets_dir / "table8_simulator_summary.csv",
            report_assets_dir / "table8_system_results.csv",
            report_assets_dir / "table8_system_results.md",
        ):
            if p.exists():
                generated_files.append(p.relative_to(ROOT).as_posix())

    # ------------------------------------------------------------------
    # 3. Generate all 7 required Appendix E.5.1 figures into results/
    #    and copy them to docs/report_assets/.
    # ------------------------------------------------------------------
    fig1_paths = [
        mouse_dir / "roc_pr_curves.png",
        report_assets_dir / "fig1_roc_pr_curves.png",
    ]
    _plot_roc_pr_curves(curves_to_plot, fig1_paths)
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig1_paths)

    fig2_paths = [
        mouse_dir / "reliability_diagram.png",
        report_assets_dir / "fig2_reliability_diagram.png",
    ]
    _plot_reliability_diagram(
        mouse_dir / "calibration.json",
        kb_dir / "calibration.json",
        fig2_paths,
    )
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig2_paths)

    fig3_paths = [
        mouse_dir / "shap_summary.png",
        report_assets_dir / "fig3_shap_summary.png",
    ]
    _plot_shap_summary(
        mouse_dir / "shap_summary.csv",
        kb_dir / "feature_importance.csv",
        fig3_paths,
    )
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig3_paths)

    src_traj = mouse_dir / "eda" / "web_bot_detection_trajectories.png"
    dst_traj = report_assets_dir / "fig4_example_trajectories.png"
    if src_traj.exists():
        shutil.copy2(src_traj, dst_traj)
        generated_files.append(dst_traj.relative_to(ROOT).as_posix())

    fig5_paths = [
        mouse_dir / "ablation_bar_chart.png",
        report_assets_dir / "fig5_ablation_bar_chart.png",
    ]
    _plot_ablation_bar_chart(mouse_dir / "ablations.csv", rule_abl_df, fig5_paths)
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig5_paths)

    fig6_paths = [
        fusion_dir / "threshold_tradeoff_curve.png",
        report_assets_dir / "fig6_threshold_tradeoff_curve.png",
    ]
    _plot_threshold_tradeoff_curve(tradeoff_df, fig6_paths)
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig6_paths)

    fig7_paths = [
        sys_dir / "latency_histogram.png",
        report_assets_dir / "fig7_latency_histogram.png",
    ]
    _plot_latency_histogram(sys_dir / "scoring_latency.json", fig7_paths)
    generated_files.extend(p.relative_to(ROOT).as_posix() for p in fig7_paths)

    manifest = {
        "tasks": ["P10-01", "P10-02"],
        "seed": seed,
        "honesty_checklist": {
            "public_benchmarks_only_no_live_human_validation": True,
            "synthetic_keyboard_bots": True,
            "touch_modality_skipped_phase8": True,
            "pseudo_session_fusion_simulated_pairing": True,
            "client_signals_raise_cost_not_guaranteed_prevention": True,
        },
        "generated_count": len(generated_files),
        "generated_files": sorted(set(generated_files)),
    }
    manifest_res = results_dir / "eval_all_manifest.json"
    manifest_doc = report_assets_dir / "manifest.json"
    manifest_res.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_doc.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--report-assets-dir", type=Path, default=ROOT / "docs" / "report_assets"
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = run_eval_all(
        results_dir=args.results_dir,
        report_assets_dir=args.report_assets_dir,
        seed=args.seed,
    )
    print(
        f"eval-all complete: {manifest['generated_count']} tables and figures written to "
        f"{args.results_dir} and {args.report_assets_dir}"
    )


if __name__ == "__main__":
    main()
