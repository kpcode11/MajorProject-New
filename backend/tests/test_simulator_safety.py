"""Unit tests for simulator target host allowlist safety guard (P7-11)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.safety import (  # noqa: E402
    DEFAULT_ALLOWLIST_PATH,
    SimulatorTargetError,
    extract_host,
    load_allowlist,
    validate_target_url,
)


def test_default_allowlist_contains_local_hosts() -> None:
    assert DEFAULT_ALLOWLIST_PATH.exists()
    allowed = load_allowlist()
    assert "localhost" in allowed
    assert "127.0.0.1" in allowed
    assert "::1" in allowed
    assert "testserver" in allowed


@pytest.mark.parametrize(
    ("url", "expected_host"),
    [
        ("http://localhost:5173", "localhost"),
        ("http://127.0.0.1:8000/portal-api/otp/request", "127.0.0.1"),
        ("http://[::1]:8000/v1/assess", "::1"),
        ("http://testserver/portal-api/otp/request", "testserver"),
    ],
)
def test_validate_target_url_accepts_allowlisted_local_hosts(url: str, expected_host: str) -> None:
    assert extract_host(url) == expected_host
    assert validate_target_url(url) == url


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://example.com/login",
        "http://192.168.1.50:8000",
        "http://10.0.0.1:8000",
        "https://myaadhaar.uidai.gov.in/",
        "https://resident.uidai.gov.in/otp",
        "https://portal.gov.in/",
        "ftp://localhost:8000",
        "http://user:pass@localhost:8000",
        "",
        "not-a-url",
    ],
)
def test_validate_target_url_refuses_non_allowlisted_or_invalid_targets(
    bad_url: str,
) -> None:
    with pytest.raises(SimulatorTargetError):
        validate_target_url(bad_url)


def test_custom_allowlist_file_and_unconditional_gov_block(tmp_path: Path) -> None:
    custom_allowlist = tmp_path / "allowlist.txt"
    custom_allowlist.write_text(
        "# Custom local test container\nmock-portal.local\nuidai.gov.in\n",
        encoding="utf-8",
    )

    # Custom local container entry in allowlist.txt is accepted
    assert (
        validate_target_url(
            "http://mock-portal.local:8000/portal-api/otp/request",
            allowlist_path=custom_allowlist,
        )
        == "http://mock-portal.local:8000/portal-api/otp/request"
    )

    # Even if a .gov.in / uidai domain is placed in allowlist.txt, it is unconditionally refused
    with pytest.raises(SimulatorTargetError, match="forbidden host"):
        validate_target_url("https://uidai.gov.in/", allowlist_path=custom_allowlist)
