"""Bot simulator package (Phase 7, localhost-only)."""

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
from simulator.tier2_playwright import (
    PlaywrightPageLike,
    build_tier2_behaviour_payload,
    build_tier2_env_signals,
    drive_tier2_playwright_page,
    run_tier2_session,
)
from simulator.tier3_stealth import (
    TIER3_INIT_SCRIPT,
    TIER3_PROFILES,
    Tier3Profile,
    apply_tier3_context_adjustments,
    build_tier3_behaviour_payload,
    build_tier3_env_signals,
    drive_tier3_playwright_page,
    run_tier3_session,
)

__all__ = [
    "BUILTIN_LOCAL_HOSTS",
    "DEFAULT_ALLOWLIST_PATH",
    "DEFAULT_TIER1_USER_AGENTS",
    "PlaywrightPageLike",
    "SimOutcome",
    "SimRunResult",
    "SimulatorTargetError",
    "TIER3_INIT_SCRIPT",
    "TIER3_PROFILES",
    "Tier3Profile",
    "apply_tier3_context_adjustments",
    "build_tier2_behaviour_payload",
    "build_tier2_env_signals",
    "build_tier3_behaviour_payload",
    "build_tier3_env_signals",
    "drive_tier2_playwright_page",
    "drive_tier3_playwright_page",
    "extract_host",
    "load_allowlist",
    "run_tier1_session",
    "run_tier2_session",
    "run_tier3_session",
    "validate_target_url",
]
