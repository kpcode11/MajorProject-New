"""Tests for scripts/check_claims.py (P10-09)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_check_claims() -> Any:
    script_path = REPO_ROOT / "scripts" / "check_claims.py"
    spec = importlib.util.spec_from_file_location("check_claims", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_claims"] = module
    spec.loader.exec_module(module)
    return module


def test_real_repo_claims_pass() -> None:
    mod = _load_check_claims()
    report = mod.run_claims_check(REPO_ROOT)
    assert report["passed"] is True, report["claim_failures"]
    assert report["claims_extracted"] >= 100
    assert report["canonical_checks_failed"] == 0
    assert report["canonical_checks_total"] == 14


def test_fabricated_claim_fails_check(tmp_path: Path) -> None:
    mod = _load_check_claims()
    fake_doc = tmp_path / "README.md"
    fake_doc.write_text(
        "# Fake Report\n\n| Model | ROC-AUC |\n| :--- | ---: |\n| `fake_model` | `0.7731` |\n",
        encoding="utf-8",
    )
    corpus = {0.9999, 0.9785, 0.5000}
    claims = mod.extract_markdown_claims(fake_doc, repo_root=tmp_path)
    assert len(claims) == 1
    assert claims[0].raw == "0.7731"
    assert mod.matches_corpus(claims[0], corpus) is False


def test_percentage_and_scientific_matching() -> None:
    mod = _load_check_claims()
    corpus = {0.92, 92.0, 7.518e-08}
    pct_claim = mod.ExtractedClaim(
        file="README.md",
        line=10,
        raw="92.0%",
        value=92.0,
        decimals=1,
        is_percent=True,
        is_scientific=False,
        context="tier4=92.0%",
    )
    sci_claim = mod.ExtractedClaim(
        file="README.md",
        line=20,
        raw="7.52e-08",
        value=7.52e-08,
        decimals=2,
        is_percent=False,
        is_scientific=True,
        context="max_abs_diff=7.52e-08",
    )
    assert mod.matches_corpus(pct_claim, corpus) is True
    assert mod.matches_corpus(sci_claim, corpus) is True
