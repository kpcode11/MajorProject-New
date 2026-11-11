"""Unit tests for the demo startup task and optional Docker Compose profile (P7-19)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]


def test_docker_compose_defines_optional_redis_and_postgres_profiles() -> None:
    """deploy/docker-compose.yml defines optional Redis and PostgreSQL services on localhost."""
    compose_path = ROOT / "deploy" / "docker-compose.yml"
    assert compose_path.exists()

    parsed = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    services = parsed.get("services")
    assert isinstance(services, dict)
    assert "redis" in services
    assert "postgres" in services

    redis_svc = services["redis"]
    postgres_svc = services["postgres"]
    assert "infra" in redis_svc.get("profiles", [])
    assert "infra" in postgres_svc.get("profiles", [])
    assert "127.0.0.1:6379:6379" in redis_svc.get("ports", [])
    assert "127.0.0.1:5432:5432" in postgres_svc.get("ports", [])


def test_tasks_demo_dry_run_configures_memory_store_sqlite_and_portal_server() -> None:
    """python scripts/tasks.py demo --dry-run outputs the backend and portal startup commands."""
    for mode in ("passive", "off"):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "tasks.py"),
                "demo",
                "--protection-mode",
                mode,
                "--dry-run",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        out = proc.stdout
        assert f"PROTECTION_MODE={mode}" in out
        assert "STORE_BACKEND=memory" in out
        assert "sqlite:///./botguard.db" in out
        assert "http://127.0.0.1:8000" in out
        assert "http://127.0.0.1:5173" in out
