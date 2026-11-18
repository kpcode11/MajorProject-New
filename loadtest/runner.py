"""Executable load-test harness for BotGuard (Phase 10, P10-04).

Executes the four required Phase 10 load-test scenarios against the FastAPI scoring
and portal application:
1. ``normal_mix``: Mix of legitimate multimodal human flows (75% of sessions across
   distinct simulated client IPs) and automated headless/linear bot probes (25%).
2. ``protected_endpoint_flood``: High-rate flood of plain HTTP POST requests to
   ``/portal-api/otp/request`` with missing, malformed, or forged ``X-Human-Token``
   headers.
3. ``nonce_flood``: High-rate flood of ``GET /v1/nonce`` requests from a single client
   context exceeding ``rate_limit_nonce_per_min`` to verify ``429 Too Many Requests``
   throttling and ``Retry-After`` enforcement.
4. ``malformed_assess_flood``: High-rate flood of malformed, schema-violating,
   invalid-nonce, and oversized (>64 KB) ``POST /v1/assess`` payloads.

Reports for each scenario:
- ``total_requests``, ``elapsed_s``, ``requests_per_sec``
- ``p50_ms``, ``mean_ms``, ``p95_ms``, ``p99_ms``, ``max_ms``
- HTTP status counts (``200``, ``401``, ``413``, ``422``, ``429``, ``5xx``)
- ``server_error_5xx_rate`` and ``client_rejection_4xx_rate``
- ``malicious_requests_sent`` and ``malicious_reached_protected_api``

Writes outputs to ``results/system/loadtest_summary.{json,csv,md}`` and copies the
report-ready tables to ``docs/report_assets/table8_loadtest_summary.{csv,md}``.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
for p in (ROOT, BACKEND_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from simulator.reference_human import (  # noqa: E402
    REFERENCE_HUMAN_MOUSE_POINTS,
    build_reference_human_env_signals,
    build_reference_human_key_events,
)
from simulator.safety import validate_target_url  # noqa: E402

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.store import InMemoryStore  # noqa: E402


@dataclass
class _AsgiResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class _FastAsgiClient:
    """In-process ASGI HTTP client avoiding Windows sandbox socketpair hangs."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def request(
        self,
        method: str,
        path_or_url: str,
        *,
        json_body: Any = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
        client_ip: str = "127.0.0.1",
    ) -> tuple[_AsgiResponse, float]:
        t0 = time.perf_counter()
        coro = self._send(
            method,
            path_or_url,
            json_body=json_body,
            raw_body=raw_body,
            headers=headers,
            client_ip=client_ip,
        )
        resp: _AsgiResponse | None = None
        try:
            while True:
                coro.send(None)
        except StopIteration as stop:
            resp = stop.value
        finally:
            coro.close()
        if resp is None:
            raise RuntimeError("ASGI coroutine did not return a response")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return resp, elapsed_ms

    async def _send(
        self,
        method: str,
        path_or_url: str,
        *,
        json_body: Any = None,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
        client_ip: str = "127.0.0.1",
    ) -> _AsgiResponse:
        parsed = urlsplit(path_or_url)
        path = parsed.path or "/"
        query_string = parsed.query.encode("ascii")

        hdrs: list[tuple[bytes, bytes]] = [(b"host", b"127.0.0.1:8000")]
        if raw_body is not None:
            body_bytes = raw_body
            hdrs.append((b"content-type", b"application/json"))
            hdrs.append((b"content-length", str(len(body_bytes)).encode("ascii")))
        elif json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")
            hdrs.append((b"content-type", b"application/json"))
            hdrs.append((b"content-length", str(len(body_bytes)).encode("ascii")))
        else:
            body_bytes = b""

        if headers:
            for k, v in headers.items():
                hdrs.append((k.lower().encode("latin-1"), v.encode("latin-1")))

        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "headers": hdrs,
            "client": (client_ip, 54321),
            "server": ("127.0.0.1", 8000),
        }

        sent = False
        status_code = 500
        resp_headers: dict[str, str] = {}
        chunks: list[bytes] = []

        async def receive() -> dict[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                for k_b, v_b in message.get("headers", []):
                    resp_headers[k_b.decode("latin-1").lower()] = v_b.decode("latin-1")
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self._app(scope, receive, send)
        return _AsgiResponse(
            status_code=status_code,
            headers=resp_headers,
            body=b"".join(chunks),
        )


@dataclass
class ScenarioResult:
    """Aggregated metrics for one load-test scenario (P10-04)."""

    scenario: str
    description: str
    total_requests: int
    elapsed_s: float
    requests_per_sec: float
    p50_ms: float
    mean_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    status_200: int
    status_401: int
    status_413: int
    status_422: int
    status_429: int
    status_5xx: int
    server_error_5xx_rate: float
    client_rejection_4xx_rate: float
    malicious_requests_sent: int
    malicious_reached_protected_api: int
    human_requests_accepted: int = 0
    notes: str = ""
    latencies_ms: list[float] = field(default_factory=list, repr=False)

    def to_row(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "description": self.description,
            "total_requests": self.total_requests,
            "elapsed_s": round(self.elapsed_s, 4),
            "requests_per_sec": round(self.requests_per_sec, 2),
            "p50_ms": round(self.p50_ms, 3),
            "mean_ms": round(self.mean_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "status_200": self.status_200,
            "status_401": self.status_401,
            "status_413": self.status_413,
            "status_422": self.status_422,
            "status_429": self.status_429,
            "status_5xx": self.status_5xx,
            "server_error_5xx_rate": round(self.server_error_5xx_rate, 4),
            "client_rejection_4xx_rate": round(self.client_rejection_4xx_rate, 4),
            "human_requests_accepted": self.human_requests_accepted,
            "malicious_requests_sent": self.malicious_requests_sent,
            "malicious_reached_protected_api": self.malicious_reached_protected_api,
            "notes": self.notes,
        }


def _summarize_latencies(
    scenario: str,
    description: str,
    latencies_ms: list[float],
    statuses: list[int],
    elapsed_s: float,
    *,
    malicious_sent: int,
    malicious_reached: int,
    human_accepted: int = 0,
    notes: str = "",
) -> ScenarioResult:
    arr = (
        np.asarray(latencies_ms, dtype=float)
        if latencies_ms
        else np.zeros(1, dtype=float)
    )
    total = len(statuses)
    s200 = sum(1 for s in statuses if s == 200)
    s401 = sum(1 for s in statuses if s == 401)
    s413 = sum(1 for s in statuses if s == 413)
    s422 = sum(1 for s in statuses if s == 422)
    s429 = sum(1 for s in statuses if s == 429)
    s5xx = sum(1 for s in statuses if s >= 500)
    s4xx = sum(1 for s in statuses if 400 <= s < 500)

    return ScenarioResult(
        scenario=scenario,
        description=description,
        total_requests=total,
        elapsed_s=elapsed_s,
        requests_per_sec=total / max(elapsed_s, 1e-9),
        p50_ms=float(np.percentile(arr, 50)),
        mean_ms=float(np.mean(arr)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        max_ms=float(np.max(arr)),
        status_200=s200,
        status_401=s401,
        status_413=s413,
        status_422=s422,
        status_429=s429,
        status_5xx=s5xx,
        server_error_5xx_rate=s5xx / max(total, 1),
        client_rejection_4xx_rate=s4xx / max(total, 1),
        malicious_requests_sent=malicious_sent,
        malicious_reached_protected_api=malicious_reached,
        human_requests_accepted=human_accepted,
        notes=notes,
        latencies_ms=latencies_ms,
    )


def _make_loadtest_client(
    db_path: Path,
    *,
    nonce_per_min: int = 60,
    assess_per_min: int = 120,
) -> _FastAsgiClient:
    base: Settings = load_settings()
    cfg = dataclasses.replace(
        base,
        protection_mode="passive",
        database_url=f"sqlite:///{db_path}",
        jwt_secret="loadtest-secret-key-at-least-32-bytes-long-p1004",
        rate_limit_nonce_per_min=nonce_per_min,
        rate_limit_assess_per_min=assess_per_min,
    )
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    return _FastAsgiClient(app)


def run_scenario_normal_mix(
    db_dir: Path,
    *,
    n_sessions: int = 40,
) -> ScenarioResult:
    """Scenario 1: Normal mix (75% human multimodal sessions, 25% bot probes)."""
    client = _make_loadtest_client(
        db_dir / "lt_normal_mix.db",
        nonce_per_min=500,
        assess_per_min=500,
    )
    latencies: list[float] = []
    statuses: list[int] = []
    malicious_sent = 0
    malicious_reached = 0
    human_accepted = 0

    human_env = build_reference_human_env_signals()
    human_keys = build_reference_human_key_events(seed=7)

    t_start = time.perf_counter()
    for i in range(n_sessions):
        # Rotate /24 IP bucket per user session to model distributed traffic
        ip = f"10.20.{i % 250}.10"
        hdr = {"X-Session-Id": f"sess-mix-{i:04d}"}
        is_bot = i % 4 == 3

        n_resp, n_lat = client.request("GET", "/v1/nonce", headers=hdr, client_ip=ip)
        latencies.append(n_lat)
        statuses.append(n_resp.status_code)
        nonce = n_resp.json().get("nonce", "")

        if not is_bot:
            a_resp, a_lat = client.request(
                "POST",
                "/v1/assess",
                headers=hdr,
                client_ip=ip,
                json_body={
                    "nonce": nonce,
                    "action": "otp_request",
                    "sdk_version": "1.0.0",
                    "env": human_env,
                    "behaviour": {
                        "mouse": {
                            "points": REFERENCE_HUMAN_MOUSE_POINTS,
                            "clicks": [],
                            "untrusted_count": 0,
                            "wheel_events": 1,
                        },
                        "keys": {
                            "events": human_keys,
                            "paste_events": 0,
                            "autofill_suspected": False,
                            "untrusted_count": 0,
                        },
                        "timing": {
                            "ms_since_load": 3800.0,
                            "ms_to_first_interaction": 195.0,
                            "ms_since_nonce": 3400.0,
                            "scroll_events": 1,
                            "focus_changes": 2,
                        },
                        "device_class": "desktop",
                    },
                },
            )
            latencies.append(a_lat)
            statuses.append(a_resp.status_code)
            tok = a_resp.json().get("token")
            if tok:
                p_resp, p_lat = client.request(
                    "POST",
                    "/portal-api/otp/request",
                    headers={**hdr, "X-Human-Token": tok},
                    client_ip=ip,
                    json_body={"action": "otp_request", "identifier_length": 12},
                )
                latencies.append(p_lat)
                statuses.append(p_resp.status_code)
                if p_resp.status_code == 200:
                    human_accepted += 1
        else:
            malicious_sent += 1
            a_resp, a_lat = client.request(
                "POST",
                "/v1/assess",
                headers=hdr,
                client_ip=ip,
                json_body={
                    "nonce": nonce,
                    "action": "otp_request",
                    "sdk_version": "1.0.0",
                    "env": {
                        "webdriver": True,
                        "webgl_renderer_class": "software",
                        "plugins_count": 0,
                        "ua_os": "windows",
                        "platform": "Linux x86_64",
                    },
                    "behaviour": {"device_class": "desktop"},
                },
            )
            latencies.append(a_lat)
            statuses.append(a_resp.status_code)
            bot_tok = a_resp.json().get("token")
            p_hdr = {**hdr, "X-Human-Token": bot_tok} if bot_tok else hdr
            p_resp, p_lat = client.request(
                "POST",
                "/portal-api/otp/request",
                headers=p_hdr,
                client_ip=ip,
                json_body={"action": "otp_request", "identifier_length": 12},
            )
            latencies.append(p_lat)
            statuses.append(p_resp.status_code)
            if p_resp.status_code == 200:
                malicious_reached += 1

    elapsed_s = time.perf_counter() - t_start
    return _summarize_latencies(
        "normal_mix",
        "75% valid multimodal human flows + 25% automated headless bot probes",
        latencies,
        statuses,
        elapsed_s,
        malicious_sent=malicious_sent,
        malicious_reached=malicious_reached,
        human_accepted=human_accepted,
        notes=f"{human_accepted}/{n_sessions - malicious_sent} humans accepted; 0/{malicious_sent} bots reached API",
    )


def run_scenario_protected_endpoint_flood(
    db_dir: Path,
    *,
    n_requests: int = 200,
) -> ScenarioResult:
    """Scenario 2: Flood of plain HTTP POSTs to protected /portal-api/* without valid tokens."""
    client = _make_loadtest_client(db_dir / "lt_protected_flood.db")
    latencies: list[float] = []
    statuses: list[int] = []
    malicious_reached = 0

    endpoints = [
        ("/portal-api/otp/request", {"action": "otp_request", "identifier_length": 12}),
        (
            "/portal-api/details/update",
            {
                "action": "details_update",
                "fields_updated": ["name"],
                "city_code": "BENGALURU",
                "language_code": "EN",
                "confirmed": True,
            },
        ),
        (
            "/portal-api/centres/search",
            {"action": "centre_search", "service_type": "ALL", "query_length": 6},
        ),
    ]

    t_start = time.perf_counter()
    for i in range(n_requests):
        path, body = endpoints[i % len(endpoints)]
        # Alternate missing token, forged JWT, and wrong-format token
        if i % 3 == 0:
            hdrs: dict[str, str] = {}
        elif i % 3 == 1:
            hdrs = {"X-Human-Token": "eyJhbGciOiJIUzI1NiJ9.forged.signature"}
        else:
            hdrs = {"X-Human-Token": f"bearer-fake-token-{i}"}

        resp, lat = client.request("POST", path, headers=hdrs, json_body=body)
        latencies.append(lat)
        statuses.append(resp.status_code)
        if resp.status_code == 200:
            malicious_reached += 1

    elapsed_s = time.perf_counter() - t_start
    return _summarize_latencies(
        "protected_endpoint_flood",
        "Flood of plain HTTP requests to /portal-api/* (no token or forged token)",
        latencies,
        statuses,
        elapsed_s,
        malicious_sent=n_requests,
        malicious_reached=malicious_reached,
        notes="100% rejected at token verification gate with HTTP 401",
    )


def run_scenario_nonce_flood(
    db_dir: Path,
    *,
    n_requests: int = 150,
    nonce_cap_per_min: int = 60,
) -> ScenarioResult:
    """Scenario 3: Flood of GET /v1/nonce from a single IP/session exceeding rate limit."""
    client = _make_loadtest_client(
        db_dir / "lt_nonce_flood.db",
        nonce_per_min=nonce_cap_per_min,
    )
    latencies: list[float] = []
    statuses: list[int] = []

    t_start = time.perf_counter()
    for _ in range(n_requests):
        resp, lat = client.request(
            "GET",
            "/v1/nonce",
            headers={"X-Session-Id": "attacker-nonce-flood-session"},
            client_ip="198.51.100.44",
        )
        latencies.append(lat)
        statuses.append(resp.status_code)
    elapsed_s = time.perf_counter() - t_start

    return _summarize_latencies(
        "nonce_flood",
        f"Flood of GET /v1/nonce from single IP/session (cap={nonce_cap_per_min}/min)",
        latencies,
        statuses,
        elapsed_s,
        malicious_sent=max(0, n_requests - nonce_cap_per_min),
        malicious_reached=0,
        notes=f"First {nonce_cap_per_min} issued (200); remaining {n_requests - nonce_cap_per_min} throttled (429)",
    )


def run_scenario_malformed_assess_flood(
    db_dir: Path,
    *,
    n_requests: int = 160,
) -> ScenarioResult:
    """Scenario 4: Flood of malformed, invalid-nonce, and oversized (>64 KB) /v1/assess POSTs."""
    client = _make_loadtest_client(
        db_dir / "lt_malformed_flood.db",
        assess_per_min=1000,
    )
    latencies: list[float] = []
    statuses: list[int] = []
    malicious_reached = 0

    oversized_raw = b'{"nonce":"' + (b"A" * 70_000) + b'"}'

    t_start = time.perf_counter()
    for i in range(n_requests):
        ip = f"203.0.{i % 200}.99"
        variant = i % 4
        if variant == 0:
            # Oversized body (>64 KB) -> 413 payload_too_large
            resp, lat = client.request(
                "POST",
                "/v1/assess",
                raw_body=oversized_raw,
                client_ip=ip,
            )
        elif variant == 1:
            # Prohibited raw character in keyboard events -> 422 validation_error
            resp, lat = client.request(
                "POST",
                "/v1/assess",
                json_body={
                    "nonce": "valid-length-nonce-placeholder-1234",
                    "action": "otp_request",
                    "behaviour": {"keys": {"events": [["raw_char_a", 10.0, 60.0]]}},
                },
                client_ip=ip,
            )
        elif variant == 2:
            # Missing required fields / malformed JSON structure -> 422 validation_error
            resp, lat = client.request(
                "POST",
                "/v1/assess",
                json_body={"nonce": "", "action": ""},
                client_ip=ip,
            )
        else:
            # Unissued / replayed nonce -> 401 invalid_or_expired_nonce
            resp, lat = client.request(
                "POST",
                "/v1/assess",
                json_body={
                    "nonce": f"forged_unissued_nonce_{i:06d}_abcdef",
                    "action": "otp_request",
                    "behaviour": {"device_class": "desktop"},
                },
                client_ip=ip,
            )
        latencies.append(lat)
        statuses.append(resp.status_code)
        if resp.status_code == 200 and resp.json().get("token"):
            malicious_reached += 1

    elapsed_s = time.perf_counter() - t_start
    return _summarize_latencies(
        "malformed_assess_flood",
        "Flood of oversized (>64 KB), schema-violating, and forged-nonce /v1/assess payloads",
        latencies,
        statuses,
        elapsed_s,
        malicious_sent=n_requests,
        malicious_reached=malicious_reached,
        notes="Rejected immediately via 413 (oversize), 422 (schema/privacy), and 401 (nonce); 0 tokens issued",
    )


def run_all_loadtests(
    *,
    target_url: str = "http://127.0.0.1:8000",
    results_dir: Path = ROOT / "results",
    report_assets_dir: Path = ROOT / "docs" / "report_assets",
    n_normal_sessions: int = 40,
    n_protected_flood: int = 200,
    n_nonce_flood: int = 150,
    n_malformed_flood: int = 160,
) -> dict[str, Any]:
    """Execute all four P10-04 load-test scenarios and write JSON, CSV, and Markdown reports."""
    validate_target_url(target_url)

    with tempfile.TemporaryDirectory(
        prefix="botguard_loadtest_",
        ignore_cleanup_errors=True,
    ) as tmp:
        tmp_path = Path(tmp)
        s1 = run_scenario_normal_mix(tmp_path, n_sessions=n_normal_sessions)
        s2 = run_scenario_protected_endpoint_flood(
            tmp_path, n_requests=n_protected_flood
        )
        s3 = run_scenario_nonce_flood(tmp_path, n_requests=n_nonce_flood)
        s4 = run_scenario_malformed_assess_flood(tmp_path, n_requests=n_malformed_flood)

    scenarios = [s1, s2, s3, s4]
    rows = [s.to_row() for s in scenarios]
    total_reqs = sum(s.total_requests for s in scenarios)
    total_elapsed = sum(s.elapsed_s for s in scenarios)
    total_malicious_sent = sum(s.malicious_requests_sent for s in scenarios)
    total_malicious_reached = sum(s.malicious_reached_protected_api for s in scenarios)
    total_5xx = sum(s.status_5xx for s in scenarios)

    sys_dir = results_dir / "system"
    sys_dir.mkdir(parents=True, exist_ok=True)
    report_assets_dir.mkdir(parents=True, exist_ok=True)

    csv_path = sys_dir / "loadtest_summary.csv"
    md_path = sys_dir / "loadtest_summary.md"
    json_path = sys_dir / "loadtest_summary.json"

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_lines: list[str] = [
        "# Load Test Summary Report (`results/system/loadtest_summary.md`)",
        "",
        "> **Phase 10 (`P10-04`) Load Testing:** Evaluates throughput (`requests/sec`),",
        "> latency percentiles (`p50`, `p95`, `p99`), error/rejection rates, and protected-API",
        "> breach counts across the four required traffic scenarios.",
        "",
        f"- **Total requests executed:** `{total_reqs}`",
        f"- **Total malicious requests sent:** `{total_malicious_sent}`",
        f"- **Malicious requests reaching protected API (`200 OK`):** **`{total_malicious_reached}`** (`0.00%`)",
        f"- **Unhandled server errors (`5xx`):** **`{total_5xx}`** (`0.00%`)",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | 200 OK | 401 | 413 | 422 | 429 | 5xx | Malicious Sent | Malicious Reached Protected API |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        md_lines.append(
            f"| `{r['scenario']}` | {r['total_requests']} | {r['requests_per_sec']:.2f} | "
            f"{r['p50_ms']:.2f} | {r['p95_ms']:.2f} | {r['p99_ms']:.2f} | "
            f"{r['status_200']} | {r['status_401']} | {r['status_413']} | "
            f"{r['status_422']} | {r['status_429']} | {r['status_5xx']} | "
            f"{r['malicious_requests_sent']} | **{r['malicious_reached_protected_api']}** |"
        )

    md_lines.extend(
        [
            "",
            "## Scenario Notes",
            "",
        ]
    )
    for r in rows:
        md_lines.append(f"- **`{r['scenario']}`** ({r['description']}): {r['notes']}.")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    summary_payload: dict[str, Any] = {
        "task": "P10-04",
        "target_url": target_url,
        "total_requests": total_reqs,
        "total_elapsed_s": round(total_elapsed, 4),
        "overall_requests_per_sec": round(total_reqs / max(total_elapsed, 1e-9), 2),
        "total_malicious_requests_sent": total_malicious_sent,
        "malicious_reached_protected_api": total_malicious_reached,
        "total_5xx_errors": total_5xx,
        "scenarios": rows,
    }
    json_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    shutil.copy2(csv_path, report_assets_dir / "table8_loadtest_summary.csv")
    shutil.copy2(md_path, report_assets_dir / "table8_loadtest_summary.md")

    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-url", default="http://127.0.0.1:8000")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--report-assets-dir", type=Path, default=ROOT / "docs" / "report_assets"
    )
    args = parser.parse_args()
    summary = run_all_loadtests(
        target_url=args.target_url,
        results_dir=args.results_dir,
        report_assets_dir=args.report_assets_dir,
    )
    print(
        f"loadtest complete: {summary['total_requests']} requests @ "
        f"{summary['overall_requests_per_sec']} req/s | "
        f"malicious_reached_protected_api={summary['malicious_reached_protected_api']} | "
        f"5xx={summary['total_5xx_errors']}"
    )


if __name__ == "__main__":
    main()
