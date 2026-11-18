"""BotGuard load testing suite (Phase 10, P10-04).

Provides:
- ``loadtest/runner.py``: Executable ASGI & localhost HTTP load-test runner for the four
  Phase 10 scenarios (``normal_mix``, ``protected_endpoint_flood``, ``nonce_flood``,
  ``malformed_assess_flood``), producing ``results/system/loadtest_summary.{json,csv,md}``.
- ``loadtest/locustfile.py``: Locust scenario definitions for external HTTP load generation.
- ``loadtest/k6_scenarios.js``: k6 scenario script for external HTTP load generation.

Safety: refuses to target any non-local host via :func:`simulator.safety.validate_target_url`.
"""
