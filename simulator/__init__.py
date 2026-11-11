"""Local-only bot and reference human simulator package (Phase 7, P7-11..P7-17)."""

from __future__ import annotations

from simulator.safety import (
    BUILTIN_LOCAL_HOSTS,
    DEFAULT_ALLOWLIST_PATH,
    SimulatorTargetError,
    extract_host,
    load_allowlist,
    validate_target_url,
)
from simulator.tier1_http import (
    DEFAULT_TIER1_USER_AGENTS,
    SimOutcome,
    SimRunResult,
    run_tier1_session,
)

__all__ = [
    "BUILTIN_LOCAL_HOSTS",
    "DEFAULT_ALLOWLIST_PATH",
    "DEFAULT_TIER1_USER_AGENTS",
    "SimOutcome",
    "SimRunResult",
    "SimulatorTargetError",
    "extract_host",
    "load_allowlist",
    "run_tier1_session",
    "validate_target_url",
]
