"""Admin API endpoints for the Phase 9 operational dashboard (P9-01).

Endpoints (all protected by ``require_admin_api_key``):
- ``GET  /admin/overview``          — Requests/min, allow/challenge/deny split,
                                      latency (mean/p50/p95), model versions, portal stats.
- ``GET  /admin/scores``            — Score distribution histogram bins and policy
                                      threshold lines per action sensitivity class.
- ``GET  /admin/assessments``       — Paginated/filterable assessment rows.
- ``GET  /admin/assessments/{id}``  — Single session detail: decision, band, rules fired,
                                      top contributing features (derived values only,
                                      never raw traces), and challenge history.
- ``GET  /admin/feedback``          — List assessments flagged as false positive / false
                                      negative (``fp`` / ``fn``).
- ``POST /admin/feedback``          — Mark or clear ``fp`` / ``fn`` feedback on an
                                      assessment (stored in DB, never auto-used for training).
- ``GET  /admin/sim-results``       — Simulator outcomes per tier and protection mode
                                      from ``results/system/sim_runs.jsonl`` + ingested runs.
- ``POST /admin/sim-results``       — Ingest simulator run records into the active server.
- ``GET  /admin/privacy``           — Retention settings, record counts, and last purge status.
- ``POST /admin/privacy/purge``     — Trigger an immediate retention purge of expired
                                      features and assessments.

Authentication & Production Note:
    For the student project prototype, ``/admin/*`` endpoints are protected by a
    static API key configured via ``ADMIN_API_KEY`` and passed in the
    ``X-Admin-Key`` header or ``Authorization: Bearer <key>``. Production
    deployments MUST replace this static key with enterprise SSO / OIDC / OAuth2
    and role-based access control (RBAC) with audit logging.
"""

from __future__ import annotations

import json
import math
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.config import Settings
from app.db import AssessmentRecord, ChallengeRecord, DatabaseManager
from app.main import ApiError
from app.policy import PolicyEngine

ROOT_DIR: Path = Path(__file__).resolve().parents[2]
DEFAULT_SIM_RUNS_PATH: Path = ROOT_DIR / "results" / "system" / "sim_runs.jsonl"

AUTH_PRODUCTION_NOTE: str = (
    "Protected by static API key (X-Admin-Key / Bearer) for student project; "
    "production deployments require SSO/OIDC/OAuth2 with role-based access control (RBAC)."
)

TRAINING_FEEDBACK_NOTE: str = (
    "Analyst feedback ('fp' / 'fn') is stored for offline review only and is never "
    "automatically used to retrain or update live models."
)


# ---------------------------------------------------------------------------
# Authentication Dependency
# ---------------------------------------------------------------------------


async def require_admin_api_key(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    """Validate the admin API key from ``X-Admin-Key`` or ``Authorization: Bearer``."""
    settings: Settings = request.app.state.settings
    expected = settings.admin_api_key
    if not expected:
        raise ApiError(401, "unauthorized_admin", "Admin API key is not configured")

    candidate = x_admin_key
    if not candidate and authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            candidate = parts[1].strip()

    if not candidate or not secrets.compare_digest(candidate, expected):
        raise ApiError(
            401,
            "unauthorized_admin",
            "Missing or invalid admin API key (provide X-Admin-Key header)",
        )
    return candidate


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class FeedbackUpdateRequest(BaseModel):
    """Request body for ``POST /admin/feedback``."""

    assessment_id: str = Field(min_length=1, max_length=64)
    feedback: Literal["fp", "fn"] | None = Field(
        default=None,
        description="Mark as 'fp' (false positive), 'fn' (false negative), or null to clear.",
    )


class SimRunIngestItem(BaseModel):
    """Single simulator run record accepted by ``POST /admin/sim-results``."""

    tier: str = Field(min_length=1, max_length=32)
    protection_mode: Literal["off", "passive"] = "passive"
    action: str = Field(default="otp_request", max_length=64)
    outcome: Literal["allowed", "challenged", "denied", "blocked-at-api"]
    portal_status: int = 200
    assess_decision: str | None = None
    assess_band: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = Field(default=0.0, ge=0.0)


class SimRunIngestRequest(BaseModel):
    """Request body for ``POST /admin/sim-results``."""

    runs: list[SimRunIngestItem] = Field(min_length=1, max_length=1000)
    replace: bool = Field(
        default=False,
        description="When True, replaces previously ingested in-memory runs.",
    )


# ---------------------------------------------------------------------------
# Serialization Helpers
# ---------------------------------------------------------------------------


def _iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _serialize_assessment_summary(row: AssessmentRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "ts": _iso_utc(row.ts),
        "session_hash": row.session_hash,
        "action": row.action,
        "device_class": row.device_class,
        "score": round(float(row.score), 4),
        "band": row.band,
        "decision": row.decision,
        "rules_fired": list(row.rules_fired or []),
        "top_factors": list(row.top_factors or []),
        "model_versions": dict(row.model_versions or {}),
        "latency_ms": round(float(row.latency_ms), 3) if row.latency_ms is not None else None,
        "degraded": bool(row.degraded),
        "feedback": row.feedback,
        "has_features": row.features is not None and len(row.features) > 0,
    }


def _serialize_assessment_detail(
    row: AssessmentRecord,
    challenges: list[ChallengeRecord],
) -> dict[str, Any]:
    base = _serialize_assessment_summary(row)
    features_dict: dict[str, float] = {}
    if isinstance(row.features, dict):
        for k, v in row.features.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)):
                features_dict[str(k)] = round(float(v), 6)

    top_contributing: list[dict[str, Any]] = []
    for factor in row.top_factors or []:
        factor_str = str(factor)
        val: float | None = features_dict.get(factor_str)
        if val is None and ":" in factor_str:
            short_key = factor_str.split(":", 1)[1]
            val = features_dict.get(short_key)
        top_contributing.append(
            {
                "feature": factor_str,
                "value": val,
            }
        )

    base["features"] = features_dict if features_dict else None
    base["features_expires_at"] = _iso_utc(row.features_expires_at)
    base["top_contributing_features"] = top_contributing
    base["challenges"] = [
        {
            "id": c.id,
            "type": c.type,
            "issued_at": _iso_utc(c.issued_at),
            "completed_at": _iso_utc(c.completed_at),
            "outcome": c.outcome,
        }
        for c in challenges
    ]
    base["privacy_note"] = (
        "Derived numerical features only; raw mouse, keyboard, and touch coordinate "
        "traces are never persisted."
    )
    return base


def _load_sim_runs(sim_runs_path: Path, ingested: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if sim_runs_path.exists():
        try:
            for line in sim_runs_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    runs.append(parsed)
        except (OSError, ValueError):
            pass
    if ingested:
        runs.extend(ingested)
    return runs


def _summarize_sim_records(runs: list[dict[str, Any]]) -> dict[str, Any]:
    modes = ("off", "passive")
    tiers = ("tier1", "tier2", "tier3", "tier4")
    by_mode: dict[str, dict[str, dict[str, Any]]] = {
        mode: {
            tier: {
                "total": 0,
                "allowed": 0,
                "challenged": 0,
                "denied": 0,
                "blocked_at_api": 0,
                "caught_rate": 0.0,
                "allow_rate": 0.0,
                "mean_latency_ms": 0.0,
            }
            for tier in tiers
        }
        for mode in modes
    }
    latencies: dict[tuple[str, str], list[float]] = {}

    for r in runs:
        mode = str(r.get("protection_mode", "passive"))
        tier = str(r.get("tier", "tier1"))
        outcome = str(r.get("outcome", "denied"))
        if mode not in by_mode:
            by_mode[mode] = {}
        if tier not in by_mode[mode]:
            by_mode[mode][tier] = {
                "total": 0,
                "allowed": 0,
                "challenged": 0,
                "denied": 0,
                "blocked_at_api": 0,
                "caught_rate": 0.0,
                "allow_rate": 0.0,
                "mean_latency_ms": 0.0,
            }
        bucket = by_mode[mode][tier]
        bucket["total"] = int(bucket["total"]) + 1
        key_outcome = "blocked_at_api" if outcome == "blocked-at-api" else outcome
        if key_outcome in ("allowed", "challenged", "denied", "blocked_at_api"):
            bucket[key_outcome] = int(bucket[key_outcome]) + 1
        lat = r.get("latency_ms")
        if isinstance(lat, (int, float)) and math.isfinite(float(lat)):
            latencies.setdefault((mode, tier), []).append(float(lat))

    flat_tiers: list[dict[str, Any]] = []
    for mode, tier_map in by_mode.items():
        for tier, counts in tier_map.items():
            tot = int(counts["total"])
            allowed = int(counts["allowed"])
            caught = (
                int(counts["challenged"]) + int(counts["denied"]) + int(counts["blocked_at_api"])
            )
            counts["allow_rate"] = round(allowed / tot, 4) if tot > 0 else 0.0
            counts["caught_rate"] = round(caught / tot, 4) if tot > 0 else 0.0
            lats = latencies.get((mode, tier), [])
            counts["mean_latency_ms"] = round(float(np.mean(lats)), 2) if lats else 0.0
            flat_tiers.append(
                {
                    "protection_mode": mode,
                    "tier": tier,
                    **counts,
                }
            )

    return {
        "total_runs": len(runs),
        "by_mode": by_mode,
        "tiers": flat_tiers,
        "disclaimer": (
            "All ML models and rule weights were frozen prior to Phase 7 on held-out "
            "public dataset splits. No model, feature, or threshold was tuned on the "
            "Phase 7 simulator."
        ),
    }


# ---------------------------------------------------------------------------
# Router Factory
# ---------------------------------------------------------------------------


def create_admin_router() -> APIRouter:
    """Create the ``/admin/*`` router protected by :func:`require_admin_api_key`."""
    router = APIRouter(
        prefix="/admin",
        tags=["admin"],
        dependencies=[Depends(require_admin_api_key)],
    )

    @router.get("/overview")
    async def get_admin_overview(
        request: Request,
        window_minutes: int = Query(default=5, ge=1, le=1440),
    ) -> dict[str, Any]:
        """Return operational overview metrics (RPM, decision split, latency, model versions)."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()
        now = datetime.now(UTC)
        window_cutoff = now - timedelta(minutes=window_minutes)
        one_min_cutoff = now - timedelta(minutes=1)

        with db.session() as sess:
            rows = list(sess.scalars(select(AssessmentRecord)))

        total = len(rows)
        decisions = {"allow": 0, "challenge": 0, "deny": 0}
        degraded_count = 0
        latencies: list[float] = []
        recent_1m = 0
        recent_window = 0

        for row in rows:
            if row.decision in decisions:
                decisions[row.decision] += 1
            if row.degraded:
                degraded_count += 1
            if row.latency_ms is not None and math.isfinite(float(row.latency_ms)):
                latencies.append(float(row.latency_ms))
            row_ts = row.ts if row.ts.tzinfo is not None else row.ts.replace(tzinfo=UTC)
            if row_ts >= one_min_cutoff:
                recent_1m += 1
            if row_ts >= window_cutoff:
                recent_window += 1

        denom = max(1, total)
        decision_rates = {
            k: round(v / denom, 4) if total > 0 else 0.0 for k, v in decisions.items()
        }

        if latencies:
            arr = np.asarray(latencies, dtype=float)
            latency_summary = {
                "mean": round(float(np.mean(arr)), 3),
                "p50": round(float(np.percentile(arr, 50)), 3),
                "p95": round(float(np.percentile(arr, 95)), 3),
            }
        else:
            latency_summary = {"mean": 0.0, "p50": 0.0, "p95": 0.0}

        rpm_window = round(recent_window / float(window_minutes), 2)
        portal_stats_obj = getattr(request.app.state, "portal_stats", None)
        portal_snapshot = portal_stats_obj.snapshot() if portal_stats_obj is not None else {}

        return {
            "total_assessments": total,
            "requests_last_1m": recent_1m,
            "requests_per_minute": max(float(recent_1m), rpm_window),
            "window_minutes": window_minutes,
            "decisions": decisions,
            "decision_rates": decision_rates,
            "latency_ms": latency_summary,
            "degraded_count": degraded_count,
            "protection_mode": request.app.state.settings.protection_mode,
            "model_versions": request.app.state.scorer.model_versions.model_dump(),
            "portal_stats": portal_snapshot,
            "auth_note": AUTH_PRODUCTION_NOTE,
        }

    @router.get("/scores")
    async def get_admin_scores(
        request: Request,
        bins: int = Query(default=20, ge=5, le=100),
        action: str | None = Query(default=None, max_length=64),
    ) -> dict[str, Any]:
        """Return risk-score distribution histogram bins and policy threshold lines."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()
        policy: PolicyEngine = request.app.state.policy

        with db.session() as sess:
            stmt = select(AssessmentRecord)
            if action:
                stmt = stmt.where(AssessmentRecord.action == action)
            rows = list(sess.scalars(stmt))

        width = 1.0 / float(bins)
        hist_bins: list[dict[str, Any]] = []
        for idx in range(bins):
            start = round(idx * width, 4)
            end = round((idx + 1) * width, 4)
            hist_bins.append(
                {
                    "bin_index": idx,
                    "bin_start": start,
                    "bin_end": end,
                    "label": f"{start:.2f}–{end:.2f}",
                    "count": 0,
                    "allow": 0,
                    "challenge": 0,
                    "deny": 0,
                }
            )

        for row in rows:
            s = max(0.0, min(1.0, float(row.score)))
            bin_idx = min(bins - 1, int(s * bins))
            bucket = hist_bins[bin_idx]
            bucket["count"] += 1
            if row.decision in ("allow", "challenge", "deny"):
                bucket[row.decision] += 1

        cfg = policy.config
        thresholds = {
            cls_name: {
                "allow_below": thr.allow_below,
                "deny_at_or_above": thr.deny_at_or_above,
            }
            for cls_name, thr in cfg.action_classes.items()
        }

        return {
            "total_scored": len(rows),
            "action_filter": action,
            "bins": hist_bins,
            "band_cutoffs": {
                "low": cfg.band_low_cutoff,
                "medium": cfg.band_medium_cutoff,
            },
            "thresholds": thresholds,
            "actions": dict(cfg.actions),
        }

    @router.get("/assessments")
    async def list_admin_assessments(
        request: Request,
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        decision: Literal["allow", "challenge", "deny"] | None = Query(default=None),
        band: Literal["low", "medium", "high"] | None = Query(default=None),
        action: str | None = Query(default=None, max_length=64),
        feedback: Literal["fp", "fn"] | None = Query(default=None),
    ) -> dict[str, Any]:
        """Return paginated and filterable assessment records ordered newest-first."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()

        with db.session() as sess:
            stmt = select(AssessmentRecord)
            count_stmt = select(func.count()).select_from(AssessmentRecord)
            if decision:
                stmt = stmt.where(AssessmentRecord.decision == decision)
                count_stmt = count_stmt.where(AssessmentRecord.decision == decision)
            if band:
                stmt = stmt.where(AssessmentRecord.band == band)
                count_stmt = count_stmt.where(AssessmentRecord.band == band)
            if action:
                stmt = stmt.where(AssessmentRecord.action == action)
                count_stmt = count_stmt.where(AssessmentRecord.action == action)
            if feedback:
                stmt = stmt.where(AssessmentRecord.feedback == feedback)
                count_stmt = count_stmt.where(AssessmentRecord.feedback == feedback)

            total = int(sess.scalar(count_stmt) or 0)
            rows = list(
                sess.scalars(stmt.order_by(AssessmentRecord.ts.desc()).offset(offset).limit(limit))
            )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [_serialize_assessment_summary(r) for r in rows],
        }

    @router.get("/assessments/{assessment_id}")
    async def get_admin_assessment_detail(
        request: Request,
        assessment_id: str,
    ) -> dict[str, Any]:
        """Return detailed session view (derived features only, never raw traces)."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()
        row = db.get_assessment(assessment_id)
        if row is None:
            raise ApiError(
                404,
                "assessment_not_found",
                f"Assessment {assessment_id!r} was not found",
            )
        challenges = db.get_challenges_for_assessment(assessment_id)
        return _serialize_assessment_detail(row, challenges)

    @router.get("/feedback")
    async def list_admin_feedback(
        request: Request,
        feedback: Literal["fp", "fn"] | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """Return analyst feedback queue items and counts of ``fp`` / ``fn`` labels."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()

        with db.session() as sess:
            fp_count = int(
                sess.scalar(
                    select(func.count())
                    .select_from(AssessmentRecord)
                    .where(AssessmentRecord.feedback == "fp")
                )
                or 0
            )
            fn_count = int(
                sess.scalar(
                    select(func.count())
                    .select_from(AssessmentRecord)
                    .where(AssessmentRecord.feedback == "fn")
                )
                or 0
            )
            stmt = select(AssessmentRecord)
            if feedback is not None:
                stmt = stmt.where(AssessmentRecord.feedback == feedback)
            else:
                stmt = stmt.where(AssessmentRecord.feedback.is_not(None))
            rows = list(sess.scalars(stmt.order_by(AssessmentRecord.ts.desc()).limit(limit)))

        return {
            "total": fp_count + fn_count,
            "fp_count": fp_count,
            "fn_count": fn_count,
            "training_policy": "stored_only_never_auto_trained",
            "note": TRAINING_FEEDBACK_NOTE,
            "items": [_serialize_assessment_summary(r) for r in rows],
        }

    @router.post("/feedback")
    async def post_admin_feedback(
        request: Request,
        payload: FeedbackUpdateRequest,
    ) -> dict[str, Any]:
        """Mark an assessment as false positive (``fp``), false negative (``fn``), or clear."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()
        updated = db.set_feedback(payload.assessment_id, payload.feedback)
        if updated is None:
            raise ApiError(
                404,
                "assessment_not_found",
                f"Assessment {payload.assessment_id!r} was not found",
            )
        return {
            "assessment_id": updated.id,
            "feedback": updated.feedback,
            "decision": updated.decision,
            "band": updated.band,
            "score": round(float(updated.score), 4),
            "action": updated.action,
            "ts": _iso_utc(updated.ts),
            "training_policy": "stored_only_never_auto_trained",
            "note": TRAINING_FEEDBACK_NOTE,
        }

    @router.get("/sim-results")
    async def get_admin_sim_results(request: Request) -> dict[str, Any]:
        """Return simulator outcomes per tier and protection mode."""
        sim_path: Path = getattr(request.app.state, "sim_runs_path", DEFAULT_SIM_RUNS_PATH)
        ingested: list[dict[str, Any]] = getattr(request.app.state, "ingested_sim_runs", [])
        runs = _load_sim_runs(sim_path, ingested)
        return _summarize_sim_records(runs)

    @router.post("/sim-results")
    async def post_admin_sim_results(
        request: Request,
        payload: SimRunIngestRequest,
    ) -> dict[str, Any]:
        """Ingest simulator run records into the server's simulator results view."""
        if not hasattr(request.app.state, "ingested_sim_runs") or payload.replace:
            request.app.state.ingested_sim_runs = []
        new_items = [item.model_dump() for item in payload.runs]
        request.app.state.ingested_sim_runs.extend(new_items)

        sim_path: Path = getattr(request.app.state, "sim_runs_path", DEFAULT_SIM_RUNS_PATH)
        runs = _load_sim_runs(sim_path, request.app.state.ingested_sim_runs)
        summary = _summarize_sim_records(runs)
        summary["ingested_count"] = len(new_items)
        return summary

    @router.get("/privacy")
    async def get_admin_privacy(request: Request) -> dict[str, Any]:
        """Return retention settings, record counts, and last purge status."""
        db: DatabaseManager = request.app.state.db
        settings: Settings = request.app.state.settings
        db.flush_buffer()
        now = datetime.now(UTC)
        assessment_cutoff = now - timedelta(seconds=db.assessment_ttl_seconds)

        with db.session() as sess:
            rows = list(sess.scalars(select(AssessmentRecord)))
            total_challenges = int(
                sess.scalar(select(func.count()).select_from(ChallengeRecord)) or 0
            )

        total_assessments = len(rows)
        with_features = 0
        expired_features = 0
        expired_assessments = 0

        for r in rows:
            if r.features is not None and len(r.features) > 0:
                with_features += 1
                if r.features_expires_at is not None:
                    exp_ts = (
                        r.features_expires_at
                        if r.features_expires_at.tzinfo is not None
                        else r.features_expires_at.replace(tzinfo=UTC)
                    )
                    if exp_ts <= now:
                        expired_features += 1
            r_ts = r.ts if r.ts.tzinfo is not None else r.ts.replace(tzinfo=UTC)
            if r_ts <= assessment_cutoff:
                expired_assessments += 1

        return {
            "retention_settings": {
                "store_features_in_db": settings.store_features_in_db,
                "feature_ttl_seconds": settings.feature_ttl_seconds,
                "feature_ttl_days": round(settings.feature_ttl_seconds / 86400.0, 2),
                "assessment_ttl_seconds": settings.assessment_ttl_seconds,
                "assessment_ttl_days": round(settings.assessment_ttl_seconds / 86400.0, 2),
            },
            "record_counts": {
                "total_assessments": total_assessments,
                "assessments_with_features": with_features,
                "expired_feature_records": expired_features,
                "expired_assessment_records": expired_assessments,
                "total_challenges": total_challenges,
                "buffered_writes": db.buffered_count,
            },
            "last_purge": {
                "last_purge_at": _iso_utc(db.last_purge_at),
                "features_purged": db.last_features_purged,
                "assessments_purged": db.last_assessments_purged,
            },
            "guarantees": [
                "Raw mouse coordinates, keystroke timings, and touch traces are never persisted.",
                "Typed characters, key identities, and form field values are never collected.",
                "Client IP addresses are coarsened to /24 (IPv4) or /48 (IPv6) buckets.",
                "Derived numerical features are disabled by default and TTL-bound when enabled.",
            ],
        }

    @router.post("/privacy/purge")
    async def post_admin_privacy_purge(request: Request) -> dict[str, Any]:
        """Run an immediate retention purge of expired feature blobs and assessments."""
        db: DatabaseManager = request.app.state.db
        db.flush_buffer()
        now = datetime.now(UTC)
        features_purged = db.purge_expired_features(now=now)
        assessments_purged = db.purge_expired_assessments(now=now)
        return {
            "purged_at": _iso_utc(now),
            "features_purged": features_purged,
            "assessments_purged": assessments_purged,
        }

    return router
