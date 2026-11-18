"""Unit tests for Phase 10 system-level results consolidation (P10-03)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_RESULTS_SCRIPT = ROOT / "scripts" / "system_results.py"


def _load_system_results_module() -> Any:
    spec = importlib.util.spec_from_file_location("system_results", SYSTEM_RESULTS_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generate_system_results_creates_simulator_latency_and_throughput_artifacts() -> None:
    """P10-03: Verify simulator tier outcomes, latency distribution, and throughput tables."""
    mod = _load_system_results_module()
    summary = mod.generate_system_results(
        results_dir=ROOT / "results",
        report_assets_dir=ROOT / "docs" / "report_assets",
    )

    assert summary["task"] == "P10-03"
    assert summary["passes_latency_target"] is True
    assert float(summary["scoring_latency_ms"]["p95"]) < 200.0
    assert float(summary["throughput_calls_per_sec"]) > 50.0
    assert len(summary["simulator_tiers"]) == 8  # 4 tiers x 2 protection modes (off, passive)

    sim_csv = ROOT / "results" / "system" / "sim_summary.csv"
    sys_csv = ROOT / "results" / "system" / "system_results.csv"
    sys_md = ROOT / "results" / "system" / "system_results.md"
    sys_json = ROOT / "results" / "system" / "system_results.json"

    for p in (sim_csv, sys_csv, sys_md, sys_json):
        assert p.exists(), f"Missing system result file: {p}"

    with sim_csv.open("r", encoding="utf-8") as fh:
        sim_rows = list(csv.DictReader(fh))
    assert len(sim_rows) == 8
    passive_rows = {r["tier"]: r for r in sim_rows if r["protection_mode"] == "passive"}
    for tier in ("tier1", "tier2", "tier3"):
        assert float(passive_rows[tier]["caught_or_blocked_rate"]) == 1.0

    saved_json = json.loads(sys_json.read_text(encoding="utf-8"))
    assert saved_json["axe_audit"]["total_violations"] == 0
