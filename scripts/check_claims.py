"""Verify that numeric claims in README.md and docs/model_card.md match results/.

Usage:
    python scripts/check_claims.py
    python scripts/check_claims.py --json results/system/claims_check.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "model_card.md",
]

# Metric-bearing table headers that signal an empirical results table.
RESULT_TABLE_HEADER_KEYWORDS = (
    "roc-auc",
    "pr-auc",
    "recall",
    "fpr",
    "brier",
    "balanced acc",
    "latency",
    "measured result",
    "windows",
    "sessions",
    "speed",
    "caught",
    "precision",
    "f1",
    "prevalence",
    "threshold",
    "game type",
    "fusion method",
    "held-out",
    "evaluation split",
    "canonical volume",
    "lr human fpr",
)

# Tables whose headers clearly describe non-result reference info (layout, docs index, etc.).
NON_RESULT_TABLE_HEADERS = (
    "component",
    "directory",
    "document / artifact",
    "responsibility",
    "intended",
    "out-of-scope",
    "policy control",
)

# Explicit non-result configuration / specification / threshold constants that legitimately
# appear in backticks in README.md or docs/model_card.md (never empirical metrics).
ALLOWED_CONFIG_CONSTANTS: set[float] = {
    0.0,
    0.01,
    0.05,
    0.20,
    0.35,
    0.50,
    0.75,
    1.0,
    1e-4,
    1e-9,
    2.0,
    3.0,
    4.0,
    5.0,
    7.0,
    8.0,
    10.0,
    13.0,
    20.0,
    24.0,
    25.0,
    30.0,
    31.0,
    38.0,
    42.0,
    48.0,
    54.0,
    95.0,
    100.0,
    108.0,
    120.0,
    200.0,
    240.0,
    500.0,
    1000.0,
    1672.0,
}

# Numeric literal regex: matches ints with commas, decimals, scientific notation, optional %.
NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9_./:-])"
    r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)"
    r"(%?)"
    r"(?![A-Za-z0-9_./:-])"
)

BACKTICK_RE = re.compile(r"`([^`]+)`")
URL_OR_DOI_RE = re.compile(r"https?://\S+|10\.\d{4,9}/\S+")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
CODE_TOKEN_SKIP_RE = re.compile(
    r"(?i)(?:\.py|\.md|\.csv|\.json|\.png|\.yaml|\.tsx?|\.onnx|/|v\d|r\d{2}|p\d+-|k[1-4]|tier\s*\d|tercile_\d|phase\s*\d|sih\d+|doi|http|python|node|wcag|b101|hs256|cc\s+by|5xx|4xx|2xx)"
)


@dataclass(frozen=True)
class ExtractedClaim:
    file: str
    line: int
    raw: str
    value: float
    decimals: int
    is_percent: bool
    is_scientific: bool
    context: str


@dataclass(frozen=True)
class ClaimCheckFailure:
    file: str
    line: int
    raw: str
    value: float
    reason: str
    context: str


@dataclass(frozen=True)
class CanonicalCheckResult:
    name: str
    source: str
    expected: float
    formatted: str
    found_in: list[str]
    passed: bool
    detail: str


def _parse_float(token: str) -> float | None:
    cleaned = token.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        val = float(cleaned)
    except ValueError:
        return None
    if not math.isfinite(val):
        return None
    return val


def _decimal_places(token: str) -> int:
    cleaned = token.replace(",", "").strip().lower()
    if "e" in cleaned:
        mantissa = cleaned.split("e", 1)[0]
        return len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
    if "." in cleaned:
        return len(cleaned.split(".", 1)[1])
    return 0


def _walk_json_numbers(obj: Any, out: set[float], key_hint: str = "") -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        val = float(obj)
        if math.isfinite(val):
            out.add(val)
            if 0.0 <= val <= 1.0:
                out.add(val * 100.0)
            if "bytes" in key_hint.lower():
                out.add(val / 1024.0)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _walk_json_numbers(v, out, str(k))
    elif isinstance(obj, list):
        for item in obj:
            _walk_json_numbers(item, out, key_hint)


def collect_result_numbers(
    results_dir: Path,
    extra_json_paths: list[Path] | None = None,
) -> set[float]:
    """Collect all measured numeric values from CSV/JSON files in results/."""
    values: set[float] = set()

    if results_dir.exists():
        for csv_path in sorted(results_dir.rglob("*.csv")):
            with csv_path.open(
                "r", encoding="utf-8", errors="replace", newline=""
            ) as fh:
                reader = csv.reader(fh)
                headers: list[str] = []
                rows_raw: list[list[str]] = []
                for row_idx, row in enumerate(reader):
                    if row_idx == 0:
                        headers = [h.strip().lower() for h in row]
                        continue
                    rows_raw.append(row)
                    for col_idx, cell in enumerate(row):
                        val = _parse_float(cell)
                        if val is not None:
                            values.add(val)
                            if 0.0 <= val <= 1.0:
                                values.add(val * 100.0)
                            if col_idx < len(headers) and "bytes" in headers[col_idx]:
                                values.add(val / 1024.0)

                # For dataset_summary.csv, also register exact per-dataset sums of count columns.
                if csv_path.name == "dataset_summary.csv" and "dataset" in headers:
                    ds_idx = headers.index("dataset")
                    for col_name in ("n_windows", "n_sessions"):
                        if col_name not in headers:
                            continue
                        col_idx = headers.index(col_name)
                        by_ds: dict[str, float] = {}
                        for row in rows_raw:
                            if len(row) <= max(ds_idx, col_idx):
                                continue
                            val = _parse_float(row[col_idx])
                            if val is not None:
                                ds = row[ds_idx].strip()
                                by_ds[ds] = by_ds.get(ds, 0.0) + val
                        values.update(by_ds.values())
                        values.add(sum(by_ds.values()))

        for json_path in sorted(results_dir.rglob("*.json")):
            if json_path.name == "claims_check.json":
                continue
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            _walk_json_numbers(data, values)

    for extra_path in extra_json_paths or []:
        if extra_path.exists():
            try:
                data = json.loads(extra_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            _walk_json_numbers(data, values)

    return values


def matches_corpus(claim: ExtractedClaim, corpus: set[float]) -> bool:
    """Return True if claim.value matches any value in corpus within rounding tolerance."""
    if claim.is_scientific:
        # Relative tolerance matching displayed significant digits (e.g. 7.52e-08 -> 1% rel).
        rel_tol = max(0.5 * (10.0 ** (-claim.decimals)) * 2.0, 1e-2)
        return any(
            math.isclose(claim.value, v, rel_tol=rel_tol, abs_tol=1e-12) for v in corpus
        )

    tol = 0.5 * (10.0 ** (-claim.decimals)) + 1e-9
    # Check direct match (corpus already includes v * 100 for proportions in [0, 1]).
    for v in corpus:
        if abs(claim.value - v) <= tol:
            return True
    # Also handle percent claims where the CSV already stored 0..100 or 0..1.
    if claim.is_percent:
        prop = claim.value / 100.0
        prop_tol = tol / 100.0 + 1e-9
        for v in corpus:
            if abs(prop - v) <= prop_tol:
                return True
    return False


def _is_result_table_header(header_line: str) -> bool:
    lower = header_line.lower()
    if any(bad in lower for bad in NON_RESULT_TABLE_HEADERS):
        return False
    return any(kw in lower for kw in RESULT_TABLE_HEADER_KEYWORDS)


def _extract_numbers_from_text(
    text: str,
    file_label: str,
    line_no: int,
    *,
    allow_plain_integers: bool,
    context: str,
) -> list[ExtractedClaim]:
    cleaned = URL_OR_DOI_RE.sub(" ", text)
    cleaned = DATE_RE.sub(" ", cleaned)
    claims: list[ExtractedClaim] = []
    for match in NUMBER_RE.finditer(cleaned):
        num_str, pct = match.group(1), match.group(2)
        val = _parse_float(num_str)
        if val is None:
            continue
        is_sci = "e" in num_str.lower()
        decimals = _decimal_places(num_str)
        is_pct = pct == "%"
        if not allow_plain_integers and decimals == 0 and not is_pct and not is_sci:
            # Skip bare integers in prose unless comma-formatted (e.g. 22,851)
            if "," not in num_str:
                continue
        if not is_pct and not is_sci and val in ALLOWED_CONFIG_CONSTANTS:
            continue
        claims.append(
            ExtractedClaim(
                file=file_label,
                line=line_no,
                raw=f"{num_str}{pct}",
                value=val,
                decimals=decimals,
                is_percent=is_pct,
                is_scientific=is_sci,
                context=context[:120],
            )
        )
    return claims


def extract_markdown_claims(
    md_path: Path, repo_root: Path = REPO_ROOT
) -> list[ExtractedClaim]:
    """Extract empirical numeric claims from result tables and backticked metrics."""
    rel = str(md_path.relative_to(repo_root)).replace("\\", "/")
    lines = md_path.read_text(encoding="utf-8").splitlines()
    claims: list[ExtractedClaim] = []

    in_code_block = False
    in_result_table = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            in_result_table = False
            continue
        if in_code_block:
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            # Detect table header vs separator vs body.
            if not in_result_table:
                if idx < len(lines) and re.match(
                    r"^\|\s*[:\-| ]+\|$", lines[idx].strip()
                ):
                    in_result_table = _is_result_table_header(stripped)
                continue
            # Skip separator row.
            if re.match(r"^\|\s*[:\-| ]+\|$", stripped):
                continue
            # Extract numbers from each non-first cell (first cell is row label like tier1/K3).
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            for cell in cells[1:]:
                if CODE_TOKEN_SKIP_RE.search(cell):
                    # Still inspect explicit backticked numbers inside mixed cells
                    for bt in BACKTICK_RE.findall(cell):
                        if CODE_TOKEN_SKIP_RE.search(bt):
                            continue
                        claims.extend(
                            _extract_numbers_from_text(
                                bt,
                                rel,
                                idx,
                                allow_plain_integers=False,
                                context=stripped,
                            )
                        )
                    continue
                claims.extend(
                    _extract_numbers_from_text(
                        cell,
                        rel,
                        idx,
                        allow_plain_integers=True,
                        context=stripped,
                    )
                )
            continue

        in_result_table = False

        # Outside tables: inspect backticked metric tokens (decimals, percentages, sci-notation).
        for bt in BACKTICK_RE.findall(stripped):
            if CODE_TOKEN_SKIP_RE.search(bt):
                continue
            claims.extend(
                _extract_numbers_from_text(
                    bt,
                    rel,
                    idx,
                    allow_plain_integers=False,
                    context=stripped,
                )
            )

    return claims


def _lookup_csv_value(
    csv_path: Path,
    filters: dict[str, str],
    column: str,
) -> float:
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if all(row.get(k, "").strip() == v for k, v in filters.items()):
                raw = row.get(column, "")
                val = _parse_float(raw)
                if val is None:
                    raise ValueError(f"Non-numeric {column}={raw!r} in {csv_path}")
                return val
    raise KeyError(f"Row matching {filters} not found in {csv_path}")


def _lookup_json_path(json_path: Path, keys: tuple[str, ...]) -> float:
    data: Any = json.loads(json_path.read_text(encoding="utf-8"))
    for key in keys:
        data = data[key]
    val = _parse_float(str(data))
    if val is None:
        raise ValueError(f"Non-numeric value at {keys} in {json_path}")
    return val


def check_canonical_claims(
    repo_root: Path = REPO_ROOT,
    docs: list[Path] | None = None,
) -> list[CanonicalCheckResult]:
    """Verify key headline metrics directly against their exact results/ source and docs."""
    doc_paths = docs or DEFAULT_DOCS
    doc_texts = {
        str(p.relative_to(repo_root)).replace("\\", "/"): p.read_text(encoding="utf-8")
        for p in doc_paths
        if p.exists()
    }

    results_dir = repo_root / "results"
    specs: list[tuple[str, str, Any, str]] = [
        (
            "mouse_in_dist_all_features_roc_auc",
            "results/mouse/evaluation_splits.csv",
            lambda: _lookup_csv_value(
                results_dir / "mouse" / "evaluation_splits.csv",
                {"model": "in_dist_all_datasets (all_features)"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "mouse_cross_phase_p1_to_p2_no_shortcuts_roc_auc",
            "results/mouse/evaluation_splits.csv",
            lambda: _lookup_csv_value(
                results_dir / "mouse" / "evaluation_splits.csv",
                {"model": "cross_phase_P1_to_P2 (no_shortcuts)"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "mouse_cross_phase_p2_to_p1_no_shortcuts_roc_auc",
            "results/mouse/evaluation_splits.csv",
            lambda: _lookup_csv_value(
                results_dir / "mouse" / "evaluation_splits.csv",
                {"model": "cross_phase_P2_to_P1 (no_shortcuts)"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "mouse_cross_dataset_ieee_no_shortcuts_roc_auc",
            "results/mouse/evaluation_splits.csv",
            lambda: _lookup_csv_value(
                results_dir / "mouse" / "evaluation_splits.csv",
                {"model": "cross_dataset_Bournemouth+DELBOT_to_IEEE (no_shortcuts)"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "mouse_lobo_gan_roc_auc",
            "results/mouse/lobo_evaluation.csv",
            lambda: _lookup_csv_value(
                results_dir / "mouse" / "lobo_evaluation.csv",
                {"held_out_bot_type": "gan"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "keyboard_lr_k3_roc_auc",
            "results/keyboard/per_generator.csv",
            lambda: _lookup_csv_value(
                results_dir / "keyboard" / "per_generator.csv",
                {"model": "logistic_regression", "generator": "K3"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "keyboard_lgbm_k3_roc_auc",
            "results/keyboard/per_generator.csv",
            lambda: _lookup_csv_value(
                results_dir / "keyboard" / "per_generator.csv",
                {"model": "lightgbm_tuned", "generator": "K3"},
                "roc_auc",
            ),
            "{:.4f}",
        ),
        (
            "fusion_stacker_brier",
            "results/fusion/fusion_comparison.csv",
            lambda: _lookup_csv_value(
                results_dir / "fusion" / "fusion_comparison.csv",
                {"group": "stacker"},
                "brier_score",
            ),
            "{:.4f}",
        ),
        (
            "system_scoring_latency_p50_ms",
            "results/system/scoring_latency.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "scoring_latency.json",
                ("latency_ms", "p50"),
            ),
            "{:.2f}",
        ),
        (
            "system_scoring_latency_p95_ms",
            "results/system/scoring_latency.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "scoring_latency.json",
                ("latency_ms", "p95"),
            ),
            "{:.2f}",
        ),
        (
            "system_scoring_throughput_rps",
            "results/system/scoring_latency.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "scoring_latency.json",
                ("throughput_calls_per_sec",),
            ),
            "{:.2f}",
        ),
        (
            "system_sdk_esm_gzip_kb",
            "results/system/sdk_size.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "sdk_size.json",
                ("bundles", "esm", "gzip_kb"),
            ),
            "{:.2f}",
        ),
        (
            "system_loadtest_throughput_rps",
            "results/system/loadtest_summary.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "loadtest_summary.json",
                ("overall_requests_per_sec",),
            ),
            "{:,.2f}",
        ),
        (
            "system_security_tests_passed",
            "results/system/security_checks.json",
            lambda: _lookup_json_path(
                results_dir / "system" / "security_checks.json",
                ("security_test_suite", "passed"),
            ),
            "{:.0f}",
        ),
    ]

    checks: list[CanonicalCheckResult] = []
    for name, source, getter, fmt in specs:
        try:
            expected = getter()
        except Exception as exc:  # pragma: no cover - surfaced as check failure
            checks.append(
                CanonicalCheckResult(
                    name=name,
                    source=source,
                    expected=float("nan"),
                    formatted="",
                    found_in=[],
                    passed=False,
                    detail=f"Failed to read source: {exc}",
                )
            )
            continue

        formatted = fmt.format(expected)
        alt_formatted = formatted.replace(",", "")
        found_in = [
            doc_name
            for doc_name, text in doc_texts.items()
            if formatted in text or alt_formatted in text
        ]
        passed = len(found_in) > 0
        checks.append(
            CanonicalCheckResult(
                name=name,
                source=source,
                expected=expected,
                formatted=formatted,
                found_in=found_in,
                passed=passed,
                detail="ok"
                if passed
                else f"Expected {formatted!r} in at least one doc",
            )
        )
    return checks


def run_claims_check(
    repo_root: Path = REPO_ROOT,
    docs: list[Path] | None = None,
) -> dict[str, Any]:
    """Run both corpus-wide numeric claim verification and canonical headline checks."""
    doc_paths = docs or [repo_root / "README.md", repo_root / "docs" / "model_card.md"]
    results_dir = repo_root / "results"
    extra_jsons = sorted((repo_root / "backend" / "models").glob("*/metadata.json"))
    corpus = collect_result_numbers(results_dir, extra_json_paths=extra_jsons)

    all_claims: list[ExtractedClaim] = []
    failures: list[ClaimCheckFailure] = []

    for doc in doc_paths:
        if not doc.exists():
            failures.append(
                ClaimCheckFailure(
                    file=str(doc),
                    line=0,
                    raw="",
                    value=0.0,
                    reason="Document does not exist",
                    context="",
                )
            )
            continue
        doc_claims = extract_markdown_claims(doc, repo_root=repo_root)
        all_claims.extend(doc_claims)
        for claim in doc_claims:
            if not matches_corpus(claim, corpus):
                failures.append(
                    ClaimCheckFailure(
                        file=claim.file,
                        line=claim.line,
                        raw=claim.raw,
                        value=claim.value,
                        reason="Value not found in results/ CSV/JSON artifacts",
                        context=claim.context,
                    )
                )

    canonical = check_canonical_claims(repo_root=repo_root, docs=doc_paths)
    canonical_failures = [c for c in canonical if not c.passed]

    return {
        "passed": len(failures) == 0 and len(canonical_failures) == 0,
        "docs_checked": [
            str(p.relative_to(repo_root)).replace("\\", "/") for p in doc_paths
        ],
        "corpus_size": len(corpus),
        "claims_extracted": len(all_claims),
        "claim_failures_count": len(failures),
        "canonical_checks_total": len(canonical),
        "canonical_checks_failed": len(canonical_failures),
        "claim_failures": [asdict(f) for f in failures],
        "canonical_checks": [asdict(c) for c in canonical],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify numeric claims in README.md and docs/model_card.md against results/."
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to write a JSON report (e.g. results/system/claims_check.json).",
    )
    args = parser.parse_args(argv)

    report = run_claims_check(REPO_ROOT)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"Claims check: {report['claims_extracted']} claims extracted across "
        f"{len(report['docs_checked'])} docs against {report['corpus_size']} result values; "
        f"{report['canonical_checks_total'] - report['canonical_checks_failed']}/"
        f"{report['canonical_checks_total']} canonical checks passed."
    )

    if report["claim_failures"]:
        print("\nUNMATCHED NUMERIC CLAIMS:")
        for f in report["claim_failures"]:
            print(
                f"  - {f['file']}:{f['line']} raw={f['raw']!r} ({f['reason']}) | {f['context']}"
            )

    for c in report["canonical_checks"]:
        if not c["passed"]:
            print(
                f"\nCANONICAL CHECK FAILED: {c['name']} ({c['source']}): {c['detail']}"
            )

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
