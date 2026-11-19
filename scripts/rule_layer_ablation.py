"""Measured rule-layer ablation over simulator bot tiers (Phase 10, P10-02).

Replays the seeded Phase 7 simulator (``seed=42``, ``n_per_tier`` sessions per tier,
``protection_mode="passive"``) against the in-process backend, captures every
``POST /v1/assess`` payload, and re-scores each payload with the real ``ModelScorer``
three ways:

- ``rules_only``: deterministic R01-R13 rule score alone;
- ``model_only``: fused mouse/keyboard ONNX model score alone (no model signal -> 0.0);
- ``combined``: the deployed ``max(model_score, rule_score)`` score.

Each score is mapped through the deployed ``PolicyEngine`` for the session's action; a
session counts as "caught" when the verdict is not ``allow``. Sessions that never reach
``/v1/assess`` (plain HTTP clients rejected at the portal API) are reported separately
because there is no payload to score. Nothing here is hardcoded: every number is computed
from the replayed sessions.

Run with the backend interpreter::

    backend\\.venv\\Scripts\\python.exe scripts/rule_layer_ablation.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "backend", ROOT / "ml" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from simulator.run_all import (  # noqa: E402
    _build_inprocess_asgi_factory,
    run_all_tiers,
)

TIERS = ("tier1", "tier2", "tier3", "tier4")
TIER_DESCRIPTIONS = {
    "tier1": "Plain HTTP client (no browser)",
    "tier2": "Default headless Playwright, direct fill/click",
    "tier3": "Playwright with automation-hiding adjustments",
    "tier4": "Playwright with Bezier mouse paths + randomised typing",
}


def run_ablation(*, n_per_tier: int = 25, seed: int = 42) -> list[dict[str, Any]]:
    """Replay the simulator, score captured assess payloads three ways, return table rows."""
    from app.main import app as default_app
    from app.schemas import AssessRequest

    scorer = default_app.state.scorer
    policy = default_app.state.policy
    inner_factory = _build_inprocess_asgi_factory()

    captured: list[tuple[int, dict[str, Any]]] = []

    def capturing_factory(mode: str, session_idx: int) -> Any:
        post_fn, get_fn = inner_factory(mode, session_idx)

        def wrapped_post(url: str, body: dict[str, Any], headers: dict[str, str]) -> Any:
            if (urlsplit(url).path or "") == "/v1/assess" and mode == "passive":
                captured.append((session_idx, body))
            return post_fn(url, body, headers)  # type: ignore[misc]

        return wrapped_post, get_fn

    results = run_all_tiers(
        "http://127.0.0.1:8000",
        n_per_tier=n_per_tier,
        protection_modes=("off", "passive"),
        seed=seed,
        output_path=None,
        transport_factory=capturing_factory,
    )

    per_mode_block = len(TIERS) * n_per_tier
    tier_sessions: dict[str, int] = {t: 0 for t in TIERS}
    for res in results:
        if res.protection_mode == "passive":
            tier_sessions[res.tier] += 1

    scored: dict[str, list[dict[str, float | str]]] = {t: [] for t in TIERS}
    for session_idx, body in captured:
        within = (session_idx - 1) % per_mode_block
        tier = TIERS[within // n_per_tier]
        request = AssessRequest(**body)
        out = scorer.score_request(request)
        action = request.action
        rules = float(out.rule_score)
        model = float(out.model_score) if out.model_score is not None else 0.0
        combined = float(out.score)
        scored[tier].append(
            {
                "rules": rules,
                "model": model,
                "combined": combined,
                "rules_verdict": policy.decide(rules, action).verdict,
                "model_verdict": policy.decide(model, action).verdict,
                "combined_verdict": policy.decide(combined, action).verdict,
            }
        )

    rows: list[dict[str, Any]] = []
    for tier in TIERS:
        sess = scored[tier]
        n = len(sess)

        def rate(key: str, sess: list[dict[str, float | str]] = sess, n: int = n) -> float:
            if n == 0:
                return float("nan")
            return round(sum(1 for s in sess if s[key] != "allow") / n, 4)

        def mean(key: str, sess: list[dict[str, float | str]] = sess, n: int = n) -> float:
            if n == 0:
                return float("nan")
            return round(sum(float(s[key]) for s in sess) / n, 4)

        rows.append(
            {
                "bot_tier": tier,
                "description": TIER_DESCRIPTIONS[tier],
                "n_sessions_total": tier_sessions[tier],
                "n_reached_assess": n,
                "n_blocked_before_assess": tier_sessions[tier] - n,
                "rules_only_caught_rate": rate("rules_verdict"),
                "model_only_caught_rate": rate("model_verdict"),
                "combined_caught_rate": rate("combined_verdict"),
                "mean_rule_score": mean("rules"),
                "mean_model_score": mean("model"),
                "mean_combined_score": mean("combined"),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-tier", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results" / "system" / "rule_layer_ablation.csv"
    )
    args = parser.parse_args()
    rows = run_ablation(n_per_tier=args.n_per_tier, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
