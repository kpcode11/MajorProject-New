"""Unit tests for the simulator batch runner simulator/run_all.py (P7-16)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.run_all import (  # noqa: E402
    _build_inprocess_asgi_factory,
    run_all_tiers,
    summarize_sim_runs,
)
from simulator.safety import SimulatorTargetError  # noqa: E402


def test_run_all_tiers_refuses_non_local_host(tmp_path: Path) -> None:
    """run_all_tiers must refuse non-allowlisted hosts before executing any sessions."""
    out = tmp_path / "sim_runs.jsonl"
    with pytest.raises(SimulatorTargetError):
        run_all_tiers("https://resident.uidai.gov.in", n_per_tier=2, output_path=out)
    assert not out.exists()


def test_run_all_tiers_writes_sim_runs_jsonl_and_summarizes(tmp_path: Path) -> None:
    """run_all_tiers writes valid JSONL lines across tiers 1-4 for off and passive modes."""
    out_jsonl = tmp_path / "sim_runs.jsonl"
    factory = _build_inprocess_asgi_factory(tmp_path)

    results = run_all_tiers(
        "http://127.0.0.1:8000",
        n_per_tier=3,
        seed=101,
        output_path=out_jsonl,
        transport_factory=factory,
    )
    assert len(results) == 24
    assert out_jsonl.exists()

    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 24

    for raw in lines:
        row = json.loads(raw)
        assert row["tier"] in ("tier1", "tier2", "tier3", "tier4")
        assert row["protection_mode"] in ("off", "passive")
        assert row["outcome"] in ("allowed", "challenged", "denied", "blocked-at-api")
        assert isinstance(row["params"], dict)
        assert isinstance(row["latency_ms"], (int, float))

    summary = summarize_sim_runs(results)
    assert summary["total_runs"] == 24
    for tier in ("tier1", "tier2", "tier3", "tier4"):
        assert summary["by_mode"]["off"][tier]["allowed"] == 3
    for tier in ("tier1", "tier2", "tier3"):
        assert summary["by_mode"]["passive"][tier]["allowed"] == 0
