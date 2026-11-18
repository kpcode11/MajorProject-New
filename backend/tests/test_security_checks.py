"""Unit tests for Phase 10 security checks report and remediations (P10-05)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SECURITY_CHECKS_SCRIPT = ROOT / "scripts" / "security_checks.py"


def _load_security_checks_module() -> Any:
    spec = importlib.util.spec_from_file_location("security_checks", SECURITY_CHECKS_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_security_checks_report_generation_and_artifacts() -> None:
    """P10-05: Verify security_checks.{json,md} record all audit outputs."""
    mod = _load_security_checks_module()
    report = mod.generate_security_checks_report(results_dir=ROOT / "results")

    assert report["task"] == "P10-05"
    assert report["security_test_suite"]["total_tests"] == 72
    assert report["security_test_suite"]["passed"] == 72
    assert report["security_test_suite"]["failed"] == 0
    assert report["bandit_static_analysis"]["post_remediation_scan"]["high"] == 0
    assert report["bandit_static_analysis"]["post_remediation_scan"]["medium"] == 0
    assert report["bandit_static_analysis"]["post_remediation_scan"]["low"] == 0
    assert report["npm_audit"]["sdk"]["production_vulnerabilities"] == 0

    json_path = ROOT / "results" / "system" / "security_checks.json"
    md_path = ROOT / "results" / "system" / "security_checks.md"
    assert json_path.exists()
    assert md_path.exists()

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["bandit_static_analysis"]["post_remediation_scan"]["exit_code"] == 0
