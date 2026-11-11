"""Mock Resident Self-Service Portal API routes under ``/portal-api/`` (P7-03, P7-04).

Routes:
- ``POST /portal-api/otp/request``     — Protected by ``require_human_token("otp_request")``.
- ``POST /portal-api/details/update``  — Protected by ``require_human_token("details_update")``.
- ``POST /portal-api/centres/search``  — Protected by ``require_human_token("centre_search")``.
- ``GET  /portal-api/stats``           — Returns accepted vs rejected call counters (overall,
                                         per action, and per rejection reason).

Privacy invariant:
- No route accepts or stores raw personal identifiers or typed text. Request models
  accept only coarse metadata (lengths, field names, and enum codes) and forbid extra keys.
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from app.main import require_human_token
from app.tokens import TokenClaims

PORTAL_ACTIONS: tuple[str, ...] = ("otp_request", "details_update", "centre_search")

PORTAL_PATH_ACTIONS: dict[str, str] = {
    "/portal-api/otp/request": "otp_request",
    "/portal-api/details/update": "details_update",
    "/portal-api/centres/search": "centre_search",
}

DEMO_CENTRES: list[dict[str, Any]] = [
    {
        "code": "DEMO-BLR-01",
        "name": "Mock Citizen Seva Kendra — Indiranagar",
        "district": "Bengaluru Urban",
        "services": ["New Enrolment", "Demographic Update", "Biometric Update"],
        "hours": "09:30 – 17:30 (Mon–Sat)",
    },
    {
        "code": "DEMO-DEL-02",
        "name": "Mock Citizen Seva Kendra — Connaught Place",
        "district": "New Delhi",
        "services": ["Demographic Update", "Mobile Number Link"],
        "hours": "10:00 – 18:00 (Mon–Fri)",
    },
    {
        "code": "DEMO-MUM-03",
        "name": "Mock Citizen Seva Kendra — Andheri West",
        "district": "Mumbai Suburban",
        "services": ["New Enrolment", "Demographic Update"],
        "hours": "09:00 – 17:00 (Mon–Sat)",
    },
]


class PortalStatsTracker:
    """Thread-safe counter tracking accepted vs rejected calls to ``/portal-api/*`` (P7-04)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._accepted = 0
        self._rejected = 0
        self._by_action: dict[str, dict[str, int]] = {
            action: {"accepted": 0, "rejected": 0} for action in PORTAL_ACTIONS
        }
        self._by_reason: dict[str, int] = {}

    def reset(self) -> None:
        """Reset all accepted/rejected counters to zero."""
        with self._lock:
            self._accepted = 0
            self._rejected = 0
            self._by_action = {action: {"accepted": 0, "rejected": 0} for action in PORTAL_ACTIONS}
            self._by_reason = {}

    def record_accepted(self, action: str) -> None:
        """Increment the accepted counter for ``action``."""
        with self._lock:
            self._accepted += 1
            bucket = self._by_action.setdefault(action, {"accepted": 0, "rejected": 0})
            bucket["accepted"] += 1

    def record_rejected(self, action: str, reason: str) -> None:
        """Increment the rejected counter for ``action`` and ``reason``."""
        with self._lock:
            self._rejected += 1
            bucket = self._by_action.setdefault(action, {"accepted": 0, "rejected": 0})
            bucket["rejected"] += 1
            self._by_reason[reason] = self._by_reason.get(reason, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of the current accepted/rejected statistics."""
        with self._lock:
            return {
                "accepted": self._accepted,
                "rejected": self._rejected,
                "total": self._accepted + self._rejected,
                "by_action": {act: dict(counts) for act, counts in self._by_action.items()},
                "by_reason": dict(self._by_reason),
            }


class OtpRequestPayload(BaseModel):
    """Coarse, non-identifying metadata for ``POST /portal-api/otp/request``."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="otp_request", max_length=64)
    identifier_length: int = Field(default=12, ge=1, le=64)


class DetailsUpdatePayload(BaseModel):
    """Coarse, non-identifying metadata for ``POST /portal-api/details/update``."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="details_update", max_length=64)
    fields_updated: list[str] = Field(default_factory=lambda: ["name"], max_length=10)
    city_code: str = Field(default="BENGALURU", max_length=64)
    language_code: str = Field(default="EN", max_length=16)
    confirmed: bool = Field(default=True)


class CentreSearchPayload(BaseModel):
    """Coarse, non-identifying metadata for ``POST /portal-api/centres/search``."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="centre_search", max_length=64)
    service_type: str = Field(default="ALL", max_length=64)
    query_length: int = Field(default=6, ge=1, le=128)


def _record_portal_accepted(request: Request, action: str) -> None:
    stats: PortalStatsTracker | None = getattr(request.app.state, "portal_stats", None)
    if stats is not None:
        stats.record_accepted(action)


def create_portal_router() -> APIRouter:
    """Create the ``/portal-api`` router with human-token protection and call statistics."""
    router = APIRouter(prefix="/portal-api", tags=["portal"])

    @router.get("/stats")
    async def get_portal_stats(request: Request) -> dict[str, Any]:
        stats: PortalStatsTracker | None = getattr(request.app.state, "portal_stats", None)
        if stats is None:
            stats = PortalStatsTracker()
            request.app.state.portal_stats = stats
        return stats.snapshot()

    @router.post("/otp/request")
    async def request_otp(
        request: Request,
        payload: OtpRequestPayload | None = Body(default=None),
        claims: TokenClaims = Depends(require_human_token("otp_request")),
    ) -> dict[str, Any]:
        body = payload or OtpRequestPayload()
        _record_portal_accepted(request, "otp_request")
        return {
            "status": "otp_sent",
            "action": claims.act,
            "band": claims.band,
            "identifier_length": body.identifier_length,
            "message": "Demo OTP dispatched for synthetic resident session.",
        }

    @router.post("/details/update")
    async def update_details(
        request: Request,
        payload: DetailsUpdatePayload | None = Body(default=None),
        claims: TokenClaims = Depends(require_human_token("details_update")),
    ) -> dict[str, Any]:
        body = payload or DetailsUpdatePayload()
        _record_portal_accepted(request, "details_update")
        return {
            "status": "details_updated",
            "action": claims.act,
            "band": claims.band,
            "fields_updated": body.fields_updated,
            "city_code": body.city_code,
            "language_code": body.language_code,
            "message": "Synthetic demographic update request recorded.",
        }

    @router.post("/centres/search")
    async def search_centres(
        request: Request,
        payload: CentreSearchPayload | None = Body(default=None),
        claims: TokenClaims = Depends(require_human_token("centre_search")),
    ) -> dict[str, Any]:
        body = payload or CentreSearchPayload()
        _record_portal_accepted(request, "centre_search")
        service_filter = body.service_type.upper()
        service_map = {
            "ENROLMENT": "New Enrolment",
            "DEMOGRAPHIC_UPDATE": "Demographic Update",
            "BIOMETRIC_UPDATE": "Biometric Update",
        }
        required_service = service_map.get(service_filter)
        centres = [
            c for c in DEMO_CENTRES if required_service is None or required_service in c["services"]
        ]
        return {
            "status": "ok",
            "action": claims.act,
            "band": claims.band,
            "service_type": body.service_type,
            "centres": centres,
            "message": f"Found {len(centres)} mock enrolment centre(s).",
        }

    return router
