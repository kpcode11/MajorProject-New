"""Backend contract tests verifying SDK-produced payloads against Pydantic schemas (P6-13)."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import (
    AssessRequest,
    AssessResponse,
    ChallengeAssessRequest,
    NonceResponse,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FIXTURE = ROOT / "data" / "fixtures" / "backend_contract_schema.json"
SDK_PAYLOADS_FIXTURE = ROOT / "data" / "fixtures" / "sdk_sample_payloads.json"


def test_exported_json_schema_matches_current_pydantic_models() -> None:
    """Ensure data/fixtures/backend_contract_schema.json stays in sync with app.schemas."""
    assert SCHEMA_FIXTURE.exists(), (
        "Missing backend_contract_schema.json; run python scripts/export_backend_json_schema.py"
    )
    saved = json.loads(SCHEMA_FIXTURE.read_text(encoding="utf-8"))
    current = {
        "AssessRequest": AssessRequest.model_json_schema(),
        "ChallengeAssessRequest": ChallengeAssessRequest.model_json_schema(),
        "AssessResponse": AssessResponse.model_json_schema(),
        "NonceResponse": NonceResponse.model_json_schema(),
    }
    assert saved == current


def test_sdk_sample_payloads_validate_against_backend_pydantic_models() -> None:
    """Validate the SDK-produced payloads in data/fixtures/sdk_sample_payloads.json."""
    assert SDK_PAYLOADS_FIXTURE.exists(), "Missing sdk_sample_payloads.json; run npm test in sdk/"
    data = json.loads(SDK_PAYLOADS_FIXTURE.read_text(encoding="utf-8"))

    assess_req = AssessRequest.model_validate(data["assess_request"])
    assert assess_req.action == "otp_request"
    assert assess_req.schema_version == 1
    assert assess_req.behaviour is not None
    assert assess_req.behaviour.mouse is not None
    assert len(assess_req.behaviour.mouse.points) == 27
    assert len(assess_req.behaviour.mouse.clicks) == 1
    assert assess_req.behaviour.keys is not None
    assert len(assess_req.behaviour.keys.events) == 6

    chal_req = ChallengeAssessRequest.model_validate(data["challenge_assess_request"])
    assert chal_req.challenge_id == "chal-contract-001"
    assert chal_req.hold_start_ms == 2500.0
    assert chal_req.hold_end_ms == 3680.0
