"""Target host allowlist safety guard for the BotGuard simulator (P7-11).

Non-negotiable rule (AGENTS.md & Phase 7):
- The target is a mock portal only. The bot simulator must refuse to run if the
  target host is not in an allowlist (``localhost``, ``127.0.0.1``, ``::1``, or
  entries in ``simulator/allowlist.txt``).
- Government or production domains (e.g. ``*.gov``, ``*.gov.in``, ``*.nic.in``,
  ``*uidai*``) are unconditionally forbidden even if added to an allowlist file.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_ALLOWLIST_PATH: Path = Path(__file__).resolve().parent / "allowlist.txt"
BUILTIN_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})
_FORBIDDEN_HOST_SUBSTRINGS: tuple[str, ...] = (".gov", ".nic.in", "uidai")


class SimulatorTargetError(ValueError):
    """Raised when the simulator is pointed at a non-allowlisted or forbidden host."""


def _normalize_host(raw_host: str) -> str:
    host = raw_host.strip().lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    return host


def load_allowlist(allowlist_path: Path | None = None) -> frozenset[str]:
    """Load allowed target hostnames from ``allowlist.txt`` plus built-in loopback hosts."""
    path = allowlist_path if allowlist_path is not None else DEFAULT_ALLOWLIST_PATH
    hosts: set[str] = set(BUILTIN_LOCAL_HOSTS)
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            normalized = _normalize_host(line)
            if normalized:
                hosts.add(normalized)
    return frozenset(hosts)


def extract_host(target_url: str) -> str:
    """Parse ``target_url`` and return its normalized hostname or raise."""
    if not target_url or not isinstance(target_url, str) or not target_url.strip():
        raise SimulatorTargetError("Target URL must be a non-empty http:// or https:// URL")

    parsed = urlsplit(target_url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SimulatorTargetError(
            f"Target URL must use http or https scheme, got {parsed.scheme!r}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise SimulatorTargetError("Target URL must not contain embedded credentials")
    if not parsed.hostname:
        raise SimulatorTargetError(f"Target URL has no hostname: {target_url!r}")

    return _normalize_host(parsed.hostname)


def validate_target_url(
    target_url: str,
    *,
    allowlist_path: Path | None = None,
) -> str:
    """Validate that ``target_url`` points to an allowlisted local host.

    Args:
        target_url: Full URL (e.g. ``http://127.0.0.1:8000`` or ``http://localhost:5173``).
        allowlist_path: Optional override path to ``allowlist.txt``.

    Returns:
        The stripped ``target_url`` when valid.

    Raises:
        SimulatorTargetError: If the URL is malformed, points to a forbidden domain,
            or its host is not in the allowlist.
    """
    hostname = extract_host(target_url)

    for forbidden in _FORBIDDEN_HOST_SUBSTRINGS:
        if forbidden in hostname:
            raise SimulatorTargetError(
                f"Refusing to run simulator against forbidden host {hostname!r}"
            )

    allowed = load_allowlist(allowlist_path)
    if hostname not in allowed:
        raise SimulatorTargetError(
            f"Refusing to run simulator against non-allowlisted host {hostname!r}. "
            f"Allowed hosts: {sorted(allowed)}"
        )

    return target_url.strip()
