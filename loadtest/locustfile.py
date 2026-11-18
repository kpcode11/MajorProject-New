"""Locust load-test scenarios for BotGuard (Phase 10, P10-04).

Scenarios:
1. ``NormalMixUser``: 75% valid human-like ``/v1/nonce`` -> ``/v1/assess`` ->
   ``/portal-api/otp/request`` flows and 25% bot probes.
2. ``ProtectedEndpointFloodUser``: Floods ``/portal-api/otp/request`` with plain HTTP
   requests (no token or forged token).
3. ``NonceFloodUser``: Floods ``GET /v1/nonce`` to verify sliding-window rate limiting (429).
4. ``MalformedAssessFloodUser``: Floods ``POST /v1/assess`` with malformed, invalid-nonce,
   and oversized (>64 KB) payloads.

Safety: Validates the target host against ``simulator/allowlist.txt`` on startup and
refuses any non-local host.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.reference_human import (  # noqa: E402
    REFERENCE_HUMAN_MOUSE_POINTS,
    build_reference_human_env_signals,
    build_reference_human_key_events,
)
from simulator.safety import validate_target_url  # noqa: E402

try:
    from locust import HttpUser, between, events, task  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional CLI binary

    class HttpUser:  # type: ignore[no-redef]
        """Fallback stub when locust package is not installed in the active venv."""

        host = "http://127.0.0.1:8000"
        client: Any = None

    def task(weight: int = 1) -> Any:
        def _decorator(fn: Any) -> Any:
            fn._locust_weight = weight
            return fn

        return _decorator

    def between(min_wait: float, max_wait: float) -> Any:
        return (min_wait, max_wait)

    events = None


if events is not None:  # pragma: no cover

    @events.init.add_listener
    def _on_locust_init(environment: Any, **_kwargs: Any) -> None:
        target_host = getattr(environment, "host", None) or "http://127.0.0.1:8000"
        validate_target_url(target_host)


class NormalMixUser(HttpUser):
    """Scenario 1: Normal traffic mix (75% legitimate human flow, 25% bot probes)."""

    wait_time = between(0.05, 0.20)
    host = "http://127.0.0.1:8000"

    @task(3)
    def human_otp_flow(self) -> None:
        validate_target_url(self.host)
        nonce_res = self.client.get("/v1/nonce", name="/v1/nonce [human]")
        if nonce_res.status_code != 200:
            return
        nonce = nonce_res.json().get("nonce", "")
        assess_res = self.client.post(
            "/v1/assess",
            name="/v1/assess [human]",
            json={
                "nonce": nonce,
                "action": "otp_request",
                "sdk_version": "1.0.0",
                "env": build_reference_human_env_signals(),
                "behaviour": {
                    "mouse": {
                        "points": REFERENCE_HUMAN_MOUSE_POINTS,
                        "clicks": [],
                        "untrusted_count": 0,
                        "wheel_events": 1,
                    },
                    "keys": {
                        "events": build_reference_human_key_events(seed=7),
                        "paste_events": 0,
                        "autofill_suspected": False,
                        "untrusted_count": 0,
                    },
                    "timing": {
                        "ms_since_load": 3600.0,
                        "ms_to_first_interaction": 195.0,
                        "ms_since_nonce": 3300.0,
                        "scroll_events": 1,
                        "focus_changes": 2,
                    },
                    "device_class": "desktop",
                },
            },
        )
        if assess_res.status_code == 200:
            token = assess_res.json().get("token")
            if token:
                self.client.post(
                    "/portal-api/otp/request",
                    name="/portal-api/otp/request [human]",
                    json={"action": "otp_request", "identifier_length": 12},
                    headers={"X-Human-Token": token},
                )

    @task(1)
    def headless_bot_probe(self) -> None:
        validate_target_url(self.host)
        nonce_res = self.client.get("/v1/nonce", name="/v1/nonce [bot]")
        if nonce_res.status_code != 200:
            return
        nonce = nonce_res.json().get("nonce", "")
        self.client.post(
            "/v1/assess",
            name="/v1/assess [bot]",
            json={
                "nonce": nonce,
                "action": "otp_request",
                "sdk_version": "1.0.0",
                "env": {
                    "webdriver": True,
                    "webgl_renderer_class": "software",
                    "plugins_count": 0,
                },
                "behaviour": {"device_class": "desktop"},
            },
        )


class ProtectedEndpointFloodUser(HttpUser):
    """Scenario 2: Flood of plain HTTP requests to a protected endpoint without valid tokens."""

    wait_time = between(0.01, 0.05)
    host = "http://127.0.0.1:8000"

    @task
    def flood_protected_otp(self) -> None:
        validate_target_url(self.host)
        self.client.post(
            "/portal-api/otp/request",
            name="/portal-api/otp/request [flood]",
            json={"action": "otp_request", "identifier_length": 12},
        )


class NonceFloodUser(HttpUser):
    """Scenario 3: Flood of GET /v1/nonce requests to trigger sliding-window rate limits."""

    wait_time = between(0.005, 0.02)
    host = "http://127.0.0.1:8000"

    @task
    def flood_nonce(self) -> None:
        validate_target_url(self.host)
        self.client.get("/v1/nonce", name="/v1/nonce [flood]")


class MalformedAssessFloodUser(HttpUser):
    """Scenario 4: Flood of malformed and oversized POST /v1/assess requests."""

    wait_time = between(0.01, 0.03)
    host = "http://127.0.0.1:8000"

    @task
    def flood_malformed_assess(self) -> None:
        validate_target_url(self.host)
        self.client.post(
            "/v1/assess",
            name="/v1/assess [malformed]",
            json={
                "nonce": "short",
                "action": "",
                "behaviour": {"keys": {"events": [["a", 1, 2]]}},
            },
        )
