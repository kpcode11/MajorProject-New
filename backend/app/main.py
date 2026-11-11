"""FastAPI application entrypoint, scoring endpoints, token middleware, and logging (P5-09..P5-12).

Endpoints:
- ``GET  /v1/nonce``            — Issue a single-use, context-bound 32-byte nonce.
- ``POST /v1/assess``           — Score environment + behavioural signals, apply
                                  risk policy, issue JWT or step-up challenge.
- ``POST /v1/assess/challenge`` — Verify a completed press-and-hold step-up challenge.
- ``POST /v1/token/verify``     — Verify and consume a single-use human JWT.
- ``GET  /v1/health``           — Report service status, DB health, and model versions.

Security & Privacy Invariants:
- Request bodies exceeding ``settings.max_body_bytes`` (64 KB default) are
  rejected immediately with ``413 Content Too Large``.
- The exact numeric risk score is **never** returned to untrusted callers; only
  the coarse ``band`` (``"low"``, ``"medium"``, ``"high"``) appears in responses.
- Structured JSON logs include ``request_id`` and coarse IP buckets (``/24`` or
  ``/48``), and explicitly strip raw IPs, payload traces, nonces, and tokens.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings, load_rule_config, load_settings
from app.db import DatabaseManager
from app.nonce import (
    NonceError,
    _coarsen_ip,
    context_hash_from_headers,
    issue_nonce,
    verify_nonce,
)
from app.policy import Decision, PolicyEngine, load_policy
from app.ratelimit import RateLimiter, RateLimitResult
from app.schemas import (
    AssessRequest,
    AssessResponse,
    ChallengeAssessRequest,
    ChallengeInfo,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ModelVersions,
    NonceResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
)
from app.scoring import ModelScorer, ScoreResult, load_scorer
from app.store import Store, build_store
from app.tokens import (
    TokenClaims,
    TokenError,
    issue_token,
    verify_token,
    verify_token_response,
)

_CHALLENGE_PREFIX = "challenge:"
CHALLENGE_TTL_SECONDS = 60
CHALLENGE_HOLD_MIN_MS = 800
CHALLENGE_HOLD_MAX_MS = 1500

# Keys that must never appear in structured log records (P5-12)
_REDACTED_LOG_KEYS: frozenset[str] = frozenset(
    {
        "ip",
        "client_ip",
        "raw_ip",
        "nonce",
        "token",
        "jwt",
        "env",
        "behaviour",
        "points",
        "events",
        "gestures",
        "clicks",
        "payload",
        "body",
        "user_agent",
    }
)

logger = logging.getLogger("botguard.api")


# ---------------------------------------------------------------------------
# P5-12 — Privacy-safe structured logging
# ---------------------------------------------------------------------------


def format_safe_log_record(
    event: str,
    *,
    request_id: str,
    client_ip: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Build a privacy-safe structured log dictionary.

    Full IP addresses and raw request/response payloads are never included.
    """
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        "request_id": request_id,
    }
    if client_ip:
        record["ip_bucket"] = _coarsen_ip(client_ip)

    for key, val in fields.items():
        if key.lower() in _REDACTED_LOG_KEYS:
            continue
        record[key] = val
    return record


def log_structured(
    event: str,
    *,
    request_id: str,
    client_ip: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Format and emit a JSON structured log line without PII or raw payloads."""
    rec = format_safe_log_record(
        event,
        request_id=request_id,
        client_ip=client_ip,
        **fields,
    )
    logger.info(json.dumps(rec, sort_keys=True))
    return rec


# ---------------------------------------------------------------------------
# Error formatting helpers
# ---------------------------------------------------------------------------


class ApiError(Exception):
    """Structured API error converted to a standard :class:`ErrorResponse`."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


def _error_json_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message[:1024],
            request_id=request_id,
        )
    ).model_dump()
    merged_headers = {"X-Request-Id": request_id}
    if headers:
        merged_headers.update(headers)
    return JSONResponse(status_code=status_code, content=body, headers=merged_headers)


# ---------------------------------------------------------------------------
# Body-size limit ASGI middleware (64 KB max body, P5-02 / P5-09 / P5-13)
# ---------------------------------------------------------------------------


class MaxBodySizeMiddleware:
    """ASGI middleware that rejects request bodies larger than ``max_bytes``."""

    def __init__(self, app: ASGIApp, *, max_bytes: int = 65536) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_id = str(uuid.uuid4())
        for hdr_k, hdr_v in scope.get("headers", []):
            if hdr_k.lower() == b"x-request-id" and hdr_v:
                req_id = hdr_v.decode("latin-1", errors="ignore")[:64] or req_id
            elif hdr_k.lower() == b"content-length":
                try:
                    if int(hdr_v.decode("ascii")) > self.max_bytes:
                        resp = _error_json_response(
                            413,
                            "payload_too_large",
                            f"Request body exceeds maximum size of {self.max_bytes} bytes",
                            req_id,
                        )
                        await resp(scope, receive, send)
                        return
                except ValueError:
                    pass

        scope.setdefault("state", {})["request_id"] = req_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                if not any(k.lower() == b"x-request-id" for k, _ in headers):
                    headers.append((b"x-request-id", req_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        total_read = 0
        too_large = False

        async def counted_receive() -> Message:
            nonlocal total_read, too_large
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                total_read += len(chunk)
                if total_read > self.max_bytes:
                    too_large = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        # Peek at body chunks if chunked/streaming without Content-Length
        buffered_messages: list[Message] = []
        if scope.get("method") in ("POST", "PUT", "PATCH"):
            while True:
                msg = await counted_receive()
                if too_large:
                    resp = _error_json_response(
                        413,
                        "payload_too_large",
                        f"Request body exceeds maximum size of {self.max_bytes} bytes",
                        req_id,
                    )
                    await resp(scope, receive, send_with_request_id)
                    return
                buffered_messages.append(msg)
                if not msg.get("more_body", False):
                    break

            msg_iter = iter(buffered_messages)

            async def replay_receive() -> Message:
                try:
                    return next(msg_iter)
                except StopIteration:
                    return await receive()

            await self.app(scope, replay_receive, send_with_request_id)
        else:
            await self.app(scope, receive, send_with_request_id)


# ---------------------------------------------------------------------------
# Request context helpers
# ---------------------------------------------------------------------------


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing:
        return existing
    hdr = request.headers.get("x-request-id", "").strip()
    rid = hdr[:64] if hdr else str(uuid.uuid4())
    request.state.request_id = rid
    return rid


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


# ---------------------------------------------------------------------------
# P5-10 — Protected-route dependency: require_human_token(action)
# ---------------------------------------------------------------------------


def require_human_token(expected_action: str) -> Callable[..., Any]:
    """Return a FastAPI dependency that validates a single-use human JWT for ``expected_action``.

    Accepts the token via ``X-Human-Token`` or ``Authorization: Bearer <token>``.
    """

    async def _dependency(
        request: Request,
        x_human_token: str | None = Header(default=None, alias="X-Human-Token"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> TokenClaims:
        settings: Settings = request.app.state.settings
        if settings.protection_mode == "off":
            now_ts = time.time()
            return TokenClaims(
                iss=settings.jwt_issuer,
                aud=settings.jwt_audience,
                act=expected_action,
                iat=now_ts,
                exp=now_ts + float(settings.jwt_expire_seconds),
                jti="protection-off",
                band="low",
            )

        raw_token = x_human_token
        if not raw_token and authorization:
            parts = authorization.strip().split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                raw_token = parts[1].strip()

        if not raw_token:
            stats = getattr(request.app.state, "portal_stats", None)
            if stats is not None and request.url.path.startswith("/portal-api/"):
                stats.record_rejected(expected_action, "missing_token")
            raise ApiError(
                401,
                "missing_token",
                "Protected route requires a valid X-Human-Token header",
            )

        store: Store = request.app.state.store
        try:
            return verify_token(
                store,
                settings,
                raw_token,
                expected_action=expected_action,
                consume=True,
            )
        except TokenError as exc:
            stats = getattr(request.app.state, "portal_stats", None)
            if stats is not None and request.url.path.startswith("/portal-api/"):
                stats.record_rejected(expected_action, exc.code)
            raise ApiError(401, exc.code, exc.message) from exc

    return _dependency


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_app(
    *,
    settings: Settings | None = None,
    store: Store | None = None,
    scorer: ModelScorer | None = None,
    policy: PolicyEngine | None = None,
    db: DatabaseManager | None = None,
) -> FastAPI:
    """Construct and configure the BotGuard FastAPI service."""
    cfg = settings or load_settings()
    backing_store = store or build_store(cfg.store_backend, redis_url=cfg.redis_url)
    rule_cfg = load_rule_config(cfg.rules_config_file)
    policy_engine = policy or load_policy(cfg.policy_config_file)
    model_scorer = scorer or load_scorer(
        cfg.models_dir,
        rule_config=rule_cfg,
        strict=False,
    )
    db_mgr = db or DatabaseManager(
        cfg.database_url,
        store_features_in_db=cfg.store_features_in_db,
        feature_ttl_seconds=cfg.feature_ttl_seconds,
        assessment_ttl_seconds=cfg.assessment_ttl_seconds,
    )
    rate_limiter = RateLimiter(backing_store, cfg)

    app = FastAPI(
        title="BotGuard Scoring API",
        version="0.1.0",
        description="Passive behavioural bot-detection scoring service (Phase 5).",
    )
    app.state.settings = cfg
    app.state.store = backing_store
    app.state.scorer = model_scorer
    app.state.policy = policy_engine
    app.state.db = db_mgr
    app.state.rate_limiter = rate_limiter

    app.add_middleware(MaxBodySizeMiddleware, max_bytes=cfg.max_body_bytes)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        rid = _request_id(request)
        log_structured(
            "api_error",
            request_id=rid,
            client_ip=_client_ip(request),
            status_code=exc.status_code,
            error_code=exc.code,
        )
        return _error_json_response(
            exc.status_code,
            exc.code,
            exc.message,
            rid,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        rid = _request_id(request)
        from app.portal import PORTAL_PATH_ACTIONS

        portal_act = PORTAL_PATH_ACTIONS.get(request.url.path)
        stats = getattr(request.app.state, "portal_stats", None)
        if portal_act is not None and stats is not None:
            stats.record_rejected(portal_act, "validation_error")
        first_err = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first_err.get("loc", []))
        msg = f"Validation error at {loc}: {first_err.get('msg', 'invalid input')}"
        log_structured(
            "validation_error",
            request_id=rid,
            client_ip=_client_ip(request),
            location=loc,
        )
        return _error_json_response(422, "validation_error", msg, rid)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        rid = _request_id(request)
        detail = str(exc.detail) if exc.detail else "HTTP error"
        return _error_json_response(exc.status_code, "http_error", detail, rid)

    # -----------------------------------------------------------------------
    # GET /v1/nonce
    # -----------------------------------------------------------------------

    @app.get("/v1/nonce", response_model=NonceResponse)
    async def get_nonce(request: Request) -> NonceResponse:
        rid = _request_id(request)
        ip = _client_ip(request)
        ua = _user_agent(request)
        ctx_hash = context_hash_from_headers(ip, ua)

        try:
            rl: RateLimitResult = app.state.rate_limiter.check_nonce(ip, session_id=ctx_hash)
        except Exception as exc:
            raise ApiError(503, "store_unavailable", "Nonce store is unavailable") from exc

        if not rl.allowed:
            raise ApiError(
                429,
                "rate_limit_exceeded",
                "Too many nonce requests; please retry later",
                headers={"Retry-After": str(rl.retry_after_seconds)},
            )

        try:
            token = issue_nonce(
                app.state.store,
                context_hash=ctx_hash,
                ttl=app.state.settings.nonce_ttl_seconds,
            )
        except Exception as exc:
            raise ApiError(503, "store_unavailable", "Unable to store nonce") from exc

        log_structured(
            "nonce_issued",
            request_id=rid,
            client_ip=ip,
            expires_in=app.state.settings.nonce_ttl_seconds,
        )
        return NonceResponse(nonce=token, expires_in=app.state.settings.nonce_ttl_seconds)

    # -----------------------------------------------------------------------
    # POST /v1/assess
    # -----------------------------------------------------------------------

    @app.post("/v1/assess", response_model=AssessResponse)
    async def post_assess(request: Request, payload: AssessRequest) -> AssessResponse:
        t0 = time.perf_counter()
        rid = _request_id(request)
        ip = _client_ip(request)
        ua = _user_agent(request)
        ctx_hash = context_hash_from_headers(ip, ua)

        # 1. Check Store / Rate Limit & Nonce with P5-11 Store/Redis fail-safe
        store_down = False
        try:
            rl = app.state.rate_limiter.check_assess(ip, session_id=ctx_hash)
        except Exception:
            store_down = True
            rl = None

        if not store_down and rl is not None and not rl.allowed:
            raise ApiError(
                429,
                "rate_limit_exceeded",
                "Too many assessment requests; please retry later",
                headers={"Retry-After": str(rl.retry_after_seconds)},
            )

        if not store_down:
            try:
                verify_nonce(app.state.store, payload.nonce, context_hash=ctx_hash)
            except NonceError as exc:
                code = str(exc)
                raise ApiError(
                    401,
                    code,
                    f"Nonce verification failed: {code}",
                ) from exc
            except Exception:
                store_down = True

        # 2. If Store/Redis is down, apply P5-11 fail-safe policy
        if store_down:
            fs_decision: Decision = app.state.policy.decide_redis_down(payload.action)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            token_str: str | None = None
            challenge_obj: ChallengeInfo | None = None
            if fs_decision.verdict == "allow":
                # Issue stateless signed JWT when store is down
                jwt_payload = {
                    "iss": app.state.settings.jwt_issuer,
                    "aud": app.state.settings.jwt_audience,
                    "act": payload.action,
                    "iat": time.time(),
                    "exp": time.time() + float(app.state.settings.jwt_expire_seconds),
                    "jti": secrets.token_urlsafe(24),
                    "band": fs_decision.band,
                }
                import jwt as pyjwt

                token_str = pyjwt.encode(
                    jwt_payload,
                    app.state.settings.jwt_secret,
                    algorithm="HS256",
                )
            elif fs_decision.verdict == "challenge":
                challenge_obj = ChallengeInfo(
                    id=secrets.token_urlsafe(16),
                    type="press_hold",
                    hold_ms=1100,
                    expires_in=CHALLENGE_TTL_SECONDS,
                )

            log_structured(
                "assessment_degraded_store_down",
                request_id=rid,
                client_ip=ip,
                action=payload.action,
                decision=fs_decision.verdict,
                band=fs_decision.band,
                degraded=True,
                latency_ms=round(latency_ms, 3),
            )
            return AssessResponse(
                decision=fs_decision.verdict,
                band=fs_decision.band,
                token=token_str,
                challenge=challenge_obj,
                request_id=rid,
                model_versions=app.state.scorer.model_versions,
                degraded=True,
            )

        # 3. Run combined rule + ONNX model scoring
        score_res: ScoreResult = app.state.scorer.score_request(payload)
        if score_res.degraded:
            decision = app.state.policy.decide_model_error(score_res.rule_score, payload.action)
        else:
            decision = app.state.policy.decide(score_res.score, payload.action, degraded=False)

        # 4. Build response token or step-up challenge
        issued_token: str | None = None
        issued_challenge: ChallengeInfo | None = None
        if decision.verdict == "allow":
            issued_token = issue_token(
                app.state.store,
                app.state.settings,
                action=payload.action,
                band=decision.band,
            )
        elif decision.verdict == "challenge":
            chal_id = secrets.token_urlsafe(18)
            hold_ms = CHALLENGE_HOLD_MIN_MS + secrets.randbelow(
                CHALLENGE_HOLD_MAX_MS - CHALLENGE_HOLD_MIN_MS + 1
            )
            issued_challenge = ChallengeInfo(
                id=chal_id,
                type="press_hold",
                hold_ms=hold_ms,
                expires_in=CHALLENGE_TTL_SECONDS,
            )
            chal_state = json.dumps(
                {
                    "assessment_id": rid,
                    "action": payload.action,
                    "hold_ms": hold_ms,
                    "context_hash": ctx_hash,
                    "original_score": score_res.score,
                }
            )
            app.state.store.set(
                f"{_CHALLENGE_PREFIX}{chal_id}",
                chal_state,
                ttl=CHALLENGE_TTL_SECONDS,
            )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        dev_cls = payload.behaviour.device_class if payload.behaviour else None

        # 5. Persist assessment & challenge (buffered automatically if DB is down)
        app.state.db.record_assessment(
            assessment_id=rid,
            session_hash=ctx_hash,
            action=payload.action,
            device_class=dev_cls,
            score=score_res.score,
            band=decision.band,
            decision=decision.verdict,
            rules_fired=score_res.fired_rules,
            top_factors=score_res.reasons,
            model_versions=score_res.model_versions.model_dump(),
            latency_ms=latency_ms,
            degraded=decision.degraded,
        )
        if issued_challenge is not None:
            app.state.db.record_challenge_issued(
                challenge_id=issued_challenge.id,
                assessment_id=rid,
                challenge_type=issued_challenge.type,
            )

        log_structured(
            "assessment_completed",
            request_id=rid,
            client_ip=ip,
            action=payload.action,
            decision=decision.verdict,
            band=decision.band,
            rules_fired=score_res.fired_rules,
            degraded=decision.degraded,
            latency_ms=round(latency_ms, 3),
        )

        return AssessResponse(
            decision=decision.verdict,
            band=decision.band,
            token=issued_token,
            challenge=issued_challenge,
            request_id=rid,
            model_versions=score_res.model_versions,
            degraded=decision.degraded,
        )

    # -----------------------------------------------------------------------
    # POST /v1/assess/challenge
    # -----------------------------------------------------------------------

    @app.post("/v1/assess/challenge", response_model=AssessResponse)
    async def post_assess_challenge(
        request: Request, payload: ChallengeAssessRequest
    ) -> AssessResponse:
        rid = _request_id(request)
        ip = _client_ip(request)
        ua = _user_agent(request)
        ctx_hash = context_hash_from_headers(ip, ua)

        rl = app.state.rate_limiter.check_challenge(ip, session_id=ctx_hash)
        if not rl.allowed:
            raise ApiError(
                429,
                "rate_limit_exceeded",
                "Too many challenge attempts; please retry later",
                headers={"Retry-After": str(rl.retry_after_seconds)},
            )

        try:
            verify_nonce(app.state.store, payload.nonce, context_hash=ctx_hash)
        except NonceError as exc:
            code = str(exc)
            raise ApiError(401, code, f"Nonce verification failed: {code}") from exc

        raw_chal = app.state.store.get_and_delete(f"{_CHALLENGE_PREFIX}{payload.challenge_id}")
        if raw_chal is None:
            raise ApiError(
                401,
                "invalid_or_expired_challenge",
                "Challenge ID is invalid, expired, or has already been used",
            )

        chal_data = json.loads(raw_chal)
        if chal_data.get("context_hash") != ctx_hash:
            raise ApiError(
                401,
                "challenge_context_mismatch",
                "Challenge context does not match caller",
            )
        if chal_data.get("action") != payload.action:
            raise ApiError(
                400,
                "challenge_action_mismatch",
                "Challenge action does not match original assessment action",
            )

        required_hold_ms = float(chal_data.get("hold_ms", 1000))
        original_score = float(chal_data.get("original_score", 0.5))
        held_ms = (
            payload.hold_end_ms - payload.hold_start_ms
            if (payload.hold_start_ms is not None and payload.hold_end_ms is not None)
            else -1.0
        )
        # Allow 15% human release tolerance up to 10 seconds
        hold_ok = required_hold_ms * 0.85 <= held_ms <= 10_000.0

        # Re-score using the original session score plus challenge features (P7-07)
        chal_rules: list[str] = []
        chal_bot_behaviour = False
        chal_score_val = original_score
        if payload.env is not None or payload.behaviour is not None:
            chal_assess_req = AssessRequest(
                nonce=payload.nonce,
                action=payload.action,
                sdk_version=payload.sdk_version,
                env=payload.env,
                behaviour=payload.behaviour,
            )
            chal_score_res: ScoreResult = app.state.scorer.score_request(chal_assess_req)
            chal_rules = list(chal_score_res.fired_rules)
            chal_score_val = 0.5 * original_score + 0.5 * chal_score_res.score
            if "R11" in chal_rules or (
                chal_score_res.model_score is not None and chal_score_res.model_score >= 0.85
            ):
                chal_bot_behaviour = True

        passed = hold_ok and not chal_bot_behaviour
        rescored_score = (
            round(max(0.0, min(chal_score_val - 0.45, 0.10)), 4)
            if passed
            else round(max(original_score, chal_score_val, 0.85), 4)
        )
        outcome = "passed" if passed else "failed"
        app.state.db.record_challenge_completed(
            challenge_id=payload.challenge_id,
            outcome=outcome,
        )

        if passed:
            tok = issue_token(
                app.state.store,
                app.state.settings,
                action=payload.action,
                band="low",
            )
            log_structured(
                "challenge_passed",
                request_id=rid,
                client_ip=ip,
                action=payload.action,
                challenge_id=payload.challenge_id,
                original_score=round(original_score, 4),
                rescored_score=rescored_score,
            )
            return AssessResponse(
                decision="allow",
                band="low",
                token=tok,
                challenge=None,
                request_id=rid,
                model_versions=app.state.scorer.model_versions,
                degraded=False,
            )

        log_structured(
            "challenge_failed",
            request_id=rid,
            client_ip=ip,
            action=payload.action,
            challenge_id=payload.challenge_id,
            original_score=round(original_score, 4),
            rescored_score=rescored_score,
            rules_fired=chal_rules,
        )
        return AssessResponse(
            decision="deny",
            band="high",
            token=None,
            challenge=None,
            request_id=rid,
            model_versions=app.state.scorer.model_versions,
            degraded=False,
        )

    # -----------------------------------------------------------------------
    # POST /v1/token/verify
    # -----------------------------------------------------------------------

    @app.post("/v1/token/verify", response_model=TokenVerifyResponse)
    async def post_token_verify(
        request: Request, payload: TokenVerifyRequest
    ) -> TokenVerifyResponse:
        rid = _request_id(request)
        resp = verify_token_response(
            app.state.store,
            app.state.settings,
            payload.token,
            expected_action=payload.expected_action,
            consume=True,
        )
        log_structured(
            "token_verified",
            request_id=rid,
            client_ip=_client_ip(request),
            valid=resp.valid,
            reason=resp.reason,
        )
        return resp

    # -----------------------------------------------------------------------
    # GET /v1/health
    # -----------------------------------------------------------------------

    @app.get("/v1/health", response_model=HealthResponse)
    async def get_health() -> HealthResponse:
        db_ok = app.state.db.ping()
        versions: ModelVersions = app.state.scorer.model_versions
        models_ok = versions.mouse is not None and versions.keyboard is not None
        status: Literal["ok", "degraded"] = "ok" if (db_ok and models_ok) else "degraded"
        return HealthResponse(
            status=status,
            model_versions=versions,
            store_backend=app.state.settings.store_backend,
            db_ok=db_ok,
        )

    from app.portal import PortalStatsTracker, create_portal_router

    app.state.portal_stats = PortalStatsTracker()
    app.include_router(create_portal_router())

    return app


app = create_app()
