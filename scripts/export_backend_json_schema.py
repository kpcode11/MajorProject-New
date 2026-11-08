"""Export canonical JSON Schemas from backend Pydantic v2 models for SDK contract testing (P6-13)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas import (  # noqa: E402
    AssessRequest,
    AssessResponse,
    ChallengeAssessRequest,
    NonceResponse,
)


def build_contract_schemas() -> dict[str, object]:
    """Return the combined JSON Schema bundle for the SDK/backend contract."""
    return {
        "AssessRequest": AssessRequest.model_json_schema(),
        "ChallengeAssessRequest": ChallengeAssessRequest.model_json_schema(),
        "AssessResponse": AssessResponse.model_json_schema(),
        "NonceResponse": NonceResponse.model_json_schema(),
    }


def main() -> int:
    output_path = ROOT / "data" / "fixtures" / "backend_contract_schema.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schemas = build_contract_schemas()
    output_path.write_text(
        json.dumps(schemas, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote backend contract JSON Schema to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
