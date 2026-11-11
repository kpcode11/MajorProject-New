"""Tier 1 bot simulator: plain HTTP client posting directly to protected portal endpoints (P7-12).

Behaviour:
- Validates the target URL against ``simulator/allowlist.txt`` via :func:`validate_target_url`
  before making any request.
- Posts directly to ``/portal-api/otp/request`` (or another ``/portal-api/*`` endpoint) using a
  plain HTTP client without a browser or DOM telemetry.
- Optionally supports an ``include_assess_attempt=True`` mode where the plain HTTP script also
  fetches ``GET /v1/nonce`` and posts an empty-telemetry ``POST /v1/assess`` before hitting
  ``/portal-api/otp/request``.
- Outcomes match Phase 7 vocabulary: ``"allowed"``, ``"challenged"``, ``"denied"``, or
  ``"blocked-at-api"``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from simulator.safety import validate_target_url

SimOutcome = Literal["allowed", "challenged", "denied", "blocked-at-api"]
HttpResponseTuple = tuple[int, dict[str, Any]]
HttpPostFn = Callable[[str, dict[str, Any], dict[str, str]], HttpResponseTuple]
HttpGetFn = Callable[[str, dict[str, str]], HttpResponseTuple]

DEFAULT_TIER1_USER_AGENTS: tuple[str, ...] = (
    "python-urllib/3.14",
    "python-requests/2.32.0",
    "curl/8.7.1",
)


@dataclass(frozen=True)
class SimRunResult:
    """Standardised simulator session outcome record (used across Tiers 1-4 and P7-16)."""

    tier: str
    protection_mode: str
    action: str
    outcome: SimOutcome
    portal_status: int
    assess_decision: str | None
    assess_band: str | None
    params: dict[str, Any]
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serialisable dictionary for ``sim_runs.jsonl``."""
        return {
            "tier": self.tier,
            "protection_mode": self.protection_mode,
            "action": self.action,
            "outcome": self.outcome,
            "portal_status": self.portal_status,
            "assess_decision": self.assess_decision,
            "assess_band": self.assess_band,
            "params": dict(self.params),
            "latency_ms": round(self.latency_ms, 3),
        }


def _urllib_post(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout_s: float = 5.0,
) -> HttpResponseTuple:
    validate_target_url(url)
    raw = json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=raw, headers=req_headers, method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            status = int(resp.status)
            payload = json.loads(resp.read().decode("utf-8") or "{}")
            return status, payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            err_body = {}
        return int(exc.code), err_body if isinstance(err_body, dict) else {}


def _urllib_get(
    url: str,
    headers: dict[str, str],
    *,
    timeout_s: float = 5.0,
) -> HttpResponseTuple:
    validate_target_url(url)
    req = urllib.request.Request(url, headers=dict(headers), method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            status = int(resp.status)
            payload = json.loads(resp.read().decode("utf-8") or "{}")
            return status, payload if isinstance(payload, dict) else {}
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            err_body = {}
        return int(exc.code), err_body if isinstance(err_body, dict) else {}


def run_tier1_session(
    base_url: str = "http://127.0.0.1:8000",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    endpoint_path: str = "/portal-api/otp/request",
    identifier_length: int = 12,
    user_agent: str = "python-urllib/3.14",
    include_assess_attempt: bool = False,
    allowlist_path: Path | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Execute one Tier 1 plain-HTTP bot session against ``base_url``.

    Args:
        base_url: Local backend base URL (validated against allowlist before any network call).
        protection_mode: Label recorded in result (``"passive"`` or ``"off"``).
        action: Protected action name (default ``"otp_request"``).
        endpoint_path: Target portal route path (default ``"/portal-api/otp/request"``).
        identifier_length: Synthetic identifier length sent in payload.
        user_agent: HTTP ``User-Agent`` header sent by the plain HTTP bot.
        include_assess_attempt: When ``False`` (default), posts directly to ``endpoint_path``
            with no token. When ``True``, first calls ``/v1/nonce`` and ``/v1/assess`` with no
            browser telemetry before calling ``endpoint_path``.
        allowlist_path: Optional custom allowlist path for :func:`validate_target_url`.
        post_fn: Optional injectable POST transport for unit tests.
        get_fn: Optional injectable GET transport for unit tests.

    Returns:
        A :class:`SimRunResult` describing the session outcome.
    """
    clean_base = validate_target_url(base_url, allowlist_path=allowlist_path).rstrip("/")
    portal_url = validate_target_url(
        f"{clean_base}/{endpoint_path.lstrip('/')}",
        allowlist_path=allowlist_path,
    )

    do_post: HttpPostFn = post_fn if post_fn is not None else _urllib_post
    do_get: HttpGetFn = get_fn if get_fn is not None else _urllib_get

    t0 = time.perf_counter()
    headers: dict[str, str] = {"User-Agent": user_agent}
    assess_decision: str | None = None
    assess_band: str | None = None

    if include_assess_attempt:
        nonce_url = validate_target_url(f"{clean_base}/v1/nonce", allowlist_path=allowlist_path)
        assess_url = validate_target_url(f"{clean_base}/v1/assess", allowlist_path=allowlist_path)
        n_status, n_body = do_get(nonce_url, headers)
        nonce = str(n_body.get("nonce", "")) if n_status == 200 else ""
        if nonce:
            a_status, a_body = do_post(
                assess_url,
                {
                    "nonce": nonce,
                    "action": action,
                    "sdk_version": "tier1-http-bot",
                },
                headers,
            )
            if a_status == 200:
                raw_dec = a_body.get("decision")
                raw_band = a_body.get("band")
                assess_decision = str(raw_dec) if isinstance(raw_dec, str) else None
                assess_band = str(raw_band) if isinstance(raw_band, str) else None
                tok = a_body.get("token")
                if isinstance(tok, str) and tok:
                    headers["X-Human-Token"] = tok

    portal_status, _ = do_post(
        portal_url,
        {"action": action, "identifier_length": identifier_length},
        headers,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    outcome: SimOutcome
    if portal_status == 200:
        outcome = "allowed"
    elif assess_decision == "challenge":
        outcome = "challenged"
    elif assess_decision == "deny":
        outcome = "denied"
    else:
        outcome = "blocked-at-api"

    return SimRunResult(
        tier="tier1",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "mode": "api_assess_plus_portal_post"
            if include_assess_attempt
            else "direct_portal_post",
            "identifier_length": identifier_length,
            "user_agent": user_agent,
        },
        latency_ms=latency_ms,
    )
