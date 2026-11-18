"""Unit tests for the Phase 10 load-test harness and scenarios (P10-04)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loadtest.runner import (  # noqa: E402
    run_all_loadtests,
    run_scenario_malformed_assess_flood,
    run_scenario_nonce_flood,
    run_scenario_normal_mix,
    run_scenario_protected_endpoint_flood,
)
from simulator.safety import SimulatorTargetError  # noqa: E402


def test_loadtest_refuses_non_local_target_host(tmp_path: Path) -> None:
    """P10-04 safety: loadtest runner refuses non-local and external hosts."""
    for bad_url in (
        "https://uidai.gov.in",
        "https://myaadhaar.uidai.gov.in",
        "http://192.168.1.50:8000",
    ):
        with pytest.raises(SimulatorTargetError):
            run_all_loadtests(
                target_url=bad_url,
                results_dir=tmp_path / "results",
                report_assets_dir=tmp_path / "assets",
                n_normal_sessions=4,
                n_protected_flood=10,
                n_nonce_flood=10,
                n_malformed_flood=10,
            )


def test_loadtest_scenarios_block_all_malicious_requests_with_zero_5xx(
    tmp_path: Path,
) -> None:
    """P10-04: Verify all 4 scenarios report rps, p50/p95/p99, 0 5xx, and 0 malicious breaches."""
    s1 = run_scenario_normal_mix(tmp_path, n_sessions=8)
    assert s1.status_5xx == 0
    assert s1.human_requests_accepted == 6
    assert s1.malicious_requests_sent == 2
    assert s1.malicious_reached_protected_api == 0
    assert s1.requests_per_sec > 0.0

    s2 = run_scenario_protected_endpoint_flood(tmp_path, n_requests=18)
    assert s2.status_401 == 18
    assert s2.status_5xx == 0
    assert s2.malicious_reached_protected_api == 0

    s3 = run_scenario_nonce_flood(tmp_path, n_requests=25, nonce_cap_per_min=10)
    assert s3.status_200 == 10
    assert s3.status_429 == 15
    assert s3.status_5xx == 0
    assert s3.malicious_reached_protected_api == 0

    s4 = run_scenario_malformed_assess_flood(tmp_path, n_requests=16)
    assert s4.status_413 == 4
    assert s4.status_422 == 8
    assert s4.status_401 == 4
    assert s4.status_5xx == 0
    assert s4.malicious_reached_protected_api == 0


def test_loadtest_summary_artifacts_exist() -> None:
    """P10-04: Verify committed loadtest_summary.{json,csv,md} artifacts under results/system/."""
    json_path = ROOT / "results" / "system" / "loadtest_summary.json"
    csv_path = ROOT / "results" / "system" / "loadtest_summary.csv"
    md_path = ROOT / "results" / "system" / "loadtest_summary.md"

    for p in (json_path, csv_path, md_path):
        assert p.exists(), f"Missing loadtest artifact: {p}"

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["task"] == "P10-04"
    assert data["malicious_reached_protected_api"] == 0
    assert data["total_5xx_errors"] == 0
    assert len(data["scenarios"]) == 4
