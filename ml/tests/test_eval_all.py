"""Unit tests for Phase 10 full evaluation and final Appendix E experiments (P10-01, P10-02)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EVAL_ALL_PATH = ROOT / "scripts" / "eval_all.py"


def _load_eval_all_module() -> Any:
    spec = importlib.util.spec_from_file_location("eval_all", EVAL_ALL_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_eval_all_artifacts_and_report_assets_exist() -> None:
    """P10-01: eval-all generates all required CSV+Markdown tables and 7 PNG figures."""
    manifest_path = ROOT / "docs" / "report_assets" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "P10-01" in manifest["tasks"]
    assert "P10-02" in manifest["tasks"]
    assert manifest["generated_count"] >= 70

    required_figures = [
        "docs/report_assets/fig1_roc_pr_curves.png",
        "docs/report_assets/fig2_reliability_diagram.png",
        "docs/report_assets/fig3_shap_summary.png",
        "docs/report_assets/fig4_example_trajectories.png",
        "docs/report_assets/fig5_ablation_bar_chart.png",
        "docs/report_assets/fig6_threshold_tradeoff_curve.png",
        "docs/report_assets/fig7_latency_histogram.png",
    ]
    for rel in required_figures:
        path = ROOT / rel
        assert path.exists(), f"Missing required figure: {rel}"
        assert path.stat().st_size > 1000

    required_tables = [
        "docs/report_assets/table1_dataset_summary.md",
        "docs/report_assets/table2a_mouse_baselines.md",
        "docs/report_assets/table2b_keyboard_baselines.md",
        "docs/report_assets/table3a_mouse_evaluation_splits.md",
        "docs/report_assets/table3b_captchasolve30k_human_fpr.md",
        "docs/report_assets/table4a_mouse_lobo.md",
        "docs/report_assets/table4b_keyboard_evaluation_splits.md",
        "docs/report_assets/table4c_keyboard_per_generator.md",
        "docs/report_assets/table4d_keyboard_speed_terciles.md",
        "docs/report_assets/table5a_mouse_feature_ablations.md",
        "docs/report_assets/table5b_rule_layer_ablation.md",
        "docs/report_assets/table6a_fusion_comparison.md",
        "docs/report_assets/table6b_modality_availability.md",
        "docs/report_assets/table7a_mouse_prevalence.md",
        "docs/report_assets/table7b_keyboard_prevalence.md",
        "docs/report_assets/table7c_threshold_tradeoff.md",
        "docs/report_assets/table8_simulator_summary.md",
    ]
    for rel in required_tables:
        path = ROOT / rel
        assert path.exists(), f"Missing required report table: {rel}"
        assert path.stat().st_size > 50


def test_prevalence_threshold_tradeoff_and_rule_ablation_calculations() -> None:
    """P10-02: Verify prevalence reweighting, threshold trade-off, and rule ablation."""
    mod = _load_eval_all_module()

    labels = np.array([0] * 100 + [1] * 100, dtype=int)
    scores = np.concatenate(
        [
            np.linspace(0.01, 0.45, 100),
            np.linspace(0.55, 0.99, 100),
        ]
    )

    prev_rows = mod.compute_prevalence_metrics(
        labels, scores, "unit_split", "mouse", prevalences=(0.01, 0.05, 0.20)
    )
    assert len(prev_rows) == 3
    assert [r["bot_prevalence"] for r in prev_rows] == [0.01, 0.05, 0.20]
    assert prev_rows[0]["precision_at_1pct_fpr"] < prev_rows[2]["precision_at_1pct_fpr"]

    tradeoff_df = mod.compute_threshold_tradeoff_table([("unit_split", labels, scores)])
    assert len(tradeoff_df) == 7
    zero_row = tradeoff_df[tradeoff_df["policy_preset"] == "zero_challenge_0.50_0.50"].iloc[0]
    wide_row = tradeoff_df[tradeoff_df["policy_preset"] == "ultra_wide_0.05_0.95"].iloc[0]
    assert float(zero_row["human_challenge_rate"]) == 0.0
    assert float(wide_row["human_challenge_rate"]) > float(zero_row["human_challenge_rate"])
    assert float(wide_row["bot_passthrough_fnr"]) <= float(zero_row["bot_passthrough_fnr"])

    rule_df = mod.compute_rule_layer_ablation(ROOT / "results" / "system" / "sim_runs.jsonl")
    assert len(rule_df) == 4
    assert set(rule_df["bot_tier"]) == {
        "tier1_http",
        "tier2_playwright",
        "tier3_stealth",
        "tier4_humanlike",
    }

    md = mod.df_to_markdown(pd.DataFrame([{"a": 1, "b": 0.12345}]), "Test Table", note="Note")
    assert "# Test Table" in md
    assert "> Note" in md
    assert "0.1235" in md
