"""HTTP request and response schemas for the BotGuard scoring API.

Covers Appendix B.2 (environment signals), B.3 (behaviour payload),
B.4 (assess request/response), the challenge flow, token verification,
health endpoint, and shared error/decision types.

Limits enforced here (Appendix B.3 and P5-02 spec):
- At most 600 mouse points, 300 key events, 20 gestures × 100 points.
- Numeric ranges are validated where meaningful (e.g. timestamps ≥ 0).
- String lengths are bounded to prevent oversized values.
- The body-size limit (64 KB) is enforced at the middleware level in
  ``main.py``; individual field limits here provide defence-in-depth.

Privacy: all environment values are coarse or bucketed.  No unique
fingerprint hash is ever computed from these signals.  Key events carry
``key_class`` only, never the raw key identity.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants (mirror Appendix B.3 limits)
# ---------------------------------------------------------------------------

MAX_MOUSE_POINTS = 600
MAX_KEY_EVENTS = 300
MAX_GESTURES = 20
MAX_GESTURE_POINTS = 100
MAX_STRING_LEN = 128  # for short categorical/identifier strings
MAX_BRANDS = 10  # hints_brands list length

# Key classes accepted in the behaviour payload (Appendix B.3).
KEY_CLASSES = frozenset(
    {"letter", "digit", "space", "punct", "modifier", "enter", "backspace", "other"}
)

# ---------------------------------------------------------------------------
# Shared annotated types
# ---------------------------------------------------------------------------

# A non-negative millisecond timestamp.
NonNegMs = Annotated[float, Field(ge=0.0)]

# A coordinate value (pixels or normalised grid units; must be finite).
CoordVal = Annotated[float, Field(ge=-1e6, le=1e6)]

# A short categorical/identifier string.
ShortStr = Annotated[str, Field(min_length=1, max_length=MAX_STRING_LEN)]

# ---------------------------------------------------------------------------
# B.2 — Environment signals
# ---------------------------------------------------------------------------


class EnvSignals(BaseModel):
    """Privacy-safe, coarse environment signals collected by the SDK.

    Every field is optional so that a missing or partial payload can be
    handled by the rule layer (rule R01_NO_PAYLOAD fires when the entire
    object is absent or empty).  Values are bucketed or categorical — no
    raw high-entropy strings are accepted.
    """

    # Automation markers
    webdriver: bool | None = Field(
        default=None,
        description="navigator.webdriver flag; true in most automation frameworks.",
    )

    # User-Agent parsed fields
    ua_family: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="Browser family in lowercase, e.g. 'chrome', 'firefox', 'safari'.",
    )
    ua_major: int | None = Field(
        default=None,
        ge=0,
        le=9999,
        description="Major version of the browser parsed from the UA string.",
    )
    ua_os: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="OS family in lowercase, e.g. 'windows', 'macos', 'linux', 'android', 'ios'.",
    )

    # Platform and client-hints
    platform: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="navigator.platform value, e.g. 'Win32', 'MacIntel', 'Linux x86_64'.",
    )
    hints_brands: list[str] | None = Field(
        default=None,
        max_length=MAX_BRANDS,
        description="Client-hints brand names, e.g. ['Chromium', 'Google Chrome'].",
    )
    hints_platform: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="Client-hints platform string, e.g. 'Windows', 'macOS'.",
    )

    # Locale and timezone
    languages_count: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Length of navigator.languages.",
    )
    lang_primary: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="First language tag, e.g. 'en-IN'. Used for timezone plausibility.",
    )
    timezone_offset_min: int | None = Field(
        default=None,
        ge=-840,
        le=840,
        description="new Date().getTimezoneOffset() in minutes (negative = east of UTC).",
    )

    # Screen and viewport (bucketed)
    screen_w_bucket: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="screen.width rounded to the nearest common resolution.",
    )
    screen_h_bucket: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="screen.height rounded to the nearest common resolution.",
    )
    viewport_w: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="window.innerWidth in pixels.",
    )
    viewport_h: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="window.innerHeight in pixels.",
    )
    outer_w: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="window.outerWidth in pixels.",
    )
    outer_h: int | None = Field(
        default=None,
        ge=0,
        le=32768,
        description="window.outerHeight in pixels.",
    )
    dpr_bucket: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="window.devicePixelRatio, bucketed (1, 1.5, 2, 3).",
    )

    # Hardware hints (bucketed)
    hw_concurrency_bucket: int | None = Field(
        default=None,
        ge=0,
        le=1024,
        description="navigator.hardwareConcurrency, bucketed.",
    )
    device_memory_bucket: float | None = Field(
        default=None,
        ge=0.0,
        le=256.0,
        description="navigator.deviceMemory in GB, bucketed (0.25, 0.5, 1, 2, 4, 8).",
    )

    # Rendering
    webgl_renderer_class: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="Classified WebGL renderer: 'hardware', 'software', 'virtual', 'unknown'.",
    )

    # Browser features
    plugins_count: int | None = Field(
        default=None,
        ge=0,
        le=500,
        description="navigator.plugins.length.",
    )

    # Touch capabilities
    max_touch_points: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="navigator.maxTouchPoints.",
    )
    touch_event_supported: bool | None = Field(
        default=None,
        description="'ontouchstart' in window or similar probe result.",
    )

    # Integrity
    native_fn_integrity_ok: bool | None = Field(
        default=None,
        description=(
            "True when toString() of key native functions matches the expected "
            "pattern; false when they have been overridden/proxied."
        ),
    )

    # Storage and visibility
    storage_available: bool | None = Field(
        default=None,
        description="True when localStorage / sessionStorage are accessible.",
    )
    visibility: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="document.visibilityState at collection time: 'visible', 'hidden', etc.",
    )

    def is_empty(self) -> bool:
        """Return True when every field is None (no signal provided)."""
        return all(v is None for v in self.model_dump().values())


# ---------------------------------------------------------------------------
# B.3 — Behaviour payload sub-models
# ---------------------------------------------------------------------------


class MousePoint(BaseModel):
    """A single mouse position sample: [x, y, t_ms].

    Accepted as a 3-element list ``[x, y, t_ms]`` from JSON.
    """

    x: CoordVal
    y: CoordVal
    t_ms: NonNegMs

    @classmethod
    def from_list(cls, data: list[float]) -> MousePoint:
        if len(data) != 3:
            raise ValueError("mouse point must be [x, y, t_ms]")
        return cls(x=data[0], y=data[1], t_ms=data[2])


class ClickEvent(BaseModel):
    """A single click event: [x, y, down_ms, up_ms]."""

    x: CoordVal
    y: CoordVal
    down_ms: NonNegMs
    up_ms: NonNegMs

    @model_validator(mode="after")
    def up_after_down(self) -> ClickEvent:
        if self.up_ms < self.down_ms:
            raise ValueError("up_ms must be ≥ down_ms")
        return self

    @classmethod
    def from_list(cls, data: list[float]) -> ClickEvent:
        if len(data) != 4:
            raise ValueError("click event must be [x, y, down_ms, up_ms]")
        return cls(x=data[0], y=data[1], down_ms=data[2], up_ms=data[3])


class MouseBehaviour(BaseModel):
    """Mouse movement and click events (Appendix B.3)."""

    points: list[list[float]] = Field(
        default_factory=list,
        max_length=MAX_MOUSE_POINTS,
        description=f"At most {MAX_MOUSE_POINTS} [x, y, t_ms] samples.",
    )
    clicks: list[list[float]] = Field(
        default_factory=list,
        max_length=MAX_MOUSE_POINTS,
        description="[x, y, down_ms, up_ms] click events.",
    )
    untrusted_count: int = Field(
        default=0,
        ge=0,
        le=MAX_MOUSE_POINTS,
        description="Number of events where isTrusted was false.",
    )
    wheel_events: int = Field(
        default=0,
        ge=0,
        le=10_000,
        description="Total count of wheel/scroll events.",
    )

    @field_validator("points", mode="before")
    @classmethod
    def validate_points(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        for item in v:
            if not isinstance(item, list) or len(item) != 3:
                raise ValueError("each mouse point must be [x, y, t_ms]")
        return v

    @field_validator("clicks", mode="before")
    @classmethod
    def validate_clicks(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        for item in v:
            if not isinstance(item, list) or len(item) != 4:
                raise ValueError("each click event must be [x, y, down_ms, up_ms]")
        return v


class KeyEvent(BaseModel):
    """A single key press/release event: [key_class, down_ms, up_ms].

    The raw key identity is never stored; only the class is transmitted.
    """

    key_class: str = Field(
        description=f"Key class, one of: {sorted(KEY_CLASSES)}",
        max_length=32,
    )
    down_ms: NonNegMs
    up_ms: NonNegMs

    @field_validator("key_class")
    @classmethod
    def key_class_valid(cls, v: str) -> str:
        if v not in KEY_CLASSES:
            raise ValueError(f"key_class must be one of {sorted(KEY_CLASSES)}, got {v!r}")
        return v

    @model_validator(mode="after")
    def up_after_down(self) -> KeyEvent:
        if self.up_ms < self.down_ms:
            raise ValueError("up_ms must be ≥ down_ms")
        return self

    @classmethod
    def from_list(cls, data: list[object]) -> KeyEvent:
        if len(data) != 3:
            raise ValueError("key event must be [key_class, down_ms, up_ms]")
        return cls(key_class=str(data[0]), down_ms=float(data[1]), up_ms=float(data[2]))  # type: ignore[arg-type]


class KeyBehaviour(BaseModel):
    """Keyboard timing events (Appendix B.3)."""

    events: list[list[object]] = Field(
        default_factory=list,
        max_length=MAX_KEY_EVENTS,
        description=f"At most {MAX_KEY_EVENTS} [key_class, down_ms, up_ms] events.",
    )
    paste_events: int = Field(
        default=0,
        ge=0,
        le=1000,
        description="Count of paste/autofill paste events.",
    )
    autofill_suspected: bool = Field(
        default=False,
        description="True when a browser autofill was detected.",
    )

    @field_validator("events", mode="before")
    @classmethod
    def validate_events(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        for item in v:
            if not isinstance(item, list) or len(item) != 3:
                raise ValueError("each key event must be [key_class, down_ms, up_ms]")
            if str(item[0]) not in KEY_CLASSES:
                raise ValueError(f"key_class must be one of {sorted(KEY_CLASSES)}, got {item[0]!r}")
        return v


class TouchPoint(BaseModel):
    """A single touch sample: [x, y, t_ms, pressure, size].

    pressure and size are optional (NaN in datasets that lack them).
    """

    x: CoordVal
    y: CoordVal
    t_ms: NonNegMs
    pressure: float | None = Field(default=None, ge=0.0, le=1.0)
    size: float | None = Field(default=None, ge=0.0, le=1e6)

    @classmethod
    def from_list(cls, data: list[float | None]) -> TouchPoint:
        if len(data) < 3:
            raise ValueError("touch point must have at least [x, y, t_ms]")
        return cls(
            x=data[0],  # type: ignore[arg-type]
            y=data[1],  # type: ignore[arg-type]
            t_ms=data[2],  # type: ignore[arg-type]
            pressure=data[3] if len(data) > 3 else None,
            size=data[4] if len(data) > 4 else None,
        )


class TouchGesture(BaseModel):
    """A single touch gesture (tap, swipe, drag, other)."""

    type: Literal["tap", "swipe", "drag", "other"] = Field(description="Gesture type.")
    points: list[list[float]] = Field(
        default_factory=list,
        max_length=MAX_GESTURE_POINTS,
        description=f"At most {MAX_GESTURE_POINTS} [x, y, t_ms, pressure?, size?] samples.",
    )


class TouchBehaviour(BaseModel):
    """Touch gesture events (Appendix B.3, Phase 8)."""

    gestures: list[TouchGesture] = Field(
        default_factory=list,
        max_length=MAX_GESTURES,
        description=f"At most {MAX_GESTURES} gestures.",
    )


class TimingSignals(BaseModel):
    """Page-level timing signals (Appendix B.3)."""

    ms_since_load: float | None = Field(
        default=None,
        ge=0.0,
        le=3_600_000.0,  # max 1 hour
        description="Milliseconds since page load.",
    )
    ms_to_first_interaction: float | None = Field(
        default=None,
        ge=0.0,
        le=3_600_000.0,
        description="Milliseconds from page load to first user interaction.",
    )
    ms_since_nonce: float | None = Field(
        default=None,
        ge=0.0,
        le=3_600_000.0,
        description="Milliseconds elapsed since the nonce was issued.",
    )
    scroll_events: int | None = Field(
        default=None,
        ge=0,
        le=100_000,
        description="Total scroll event count.",
    )
    focus_changes: int | None = Field(
        default=None,
        ge=0,
        le=10_000,
        description="Number of focus/blur transitions.",
    )


class BehaviourPayload(BaseModel):
    """Combined behaviour payload (Appendix B.3).

    All modality sub-objects are optional; missing modalities are handled
    by the missing-modality policy (absent ≠ bot).
    """

    mouse: MouseBehaviour | None = None
    keys: KeyBehaviour | None = None
    touch: TouchBehaviour | None = None
    timing: TimingSignals | None = None
    device_class: Literal["desktop", "mobile", "tablet", "unknown"] | None = Field(
        default=None,
        description="Device class reported by the SDK.",
    )


# ---------------------------------------------------------------------------
# B.4 — Request: POST /v1/assess
# ---------------------------------------------------------------------------


class AssessRequest(BaseModel):
    """Request body for ``POST /v1/assess`` (Appendix B.4).

    Body size is limited to 64 KB by middleware; field-level limits here
    provide defence-in-depth.
    """

    nonce: str = Field(
        min_length=1,
        max_length=256,
        description="Single-use nonce issued by GET /v1/nonce.",
    )
    action: str = Field(
        min_length=1,
        max_length=MAX_STRING_LEN,
        description=(
            "Action identifier matching a class in policy.yaml, "
            "e.g. 'otp_request', 'centre_search'."
        ),
    )
    sdk_version: str = Field(
        default="unknown",
        max_length=MAX_STRING_LEN,
        description="SDK version string.",
    )
    schema_version: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Payload schema version for forwards compatibility.",
    )
    client_ts: float | None = Field(
        default=None,
        ge=0.0,
        description="Client-side Unix timestamp in milliseconds.",
    )
    env: EnvSignals | None = Field(
        default=None,
        description="Environment signals (Appendix B.2).",
    )
    behaviour: BehaviourPayload | None = Field(
        default=None,
        description="Behaviour payload (Appendix B.3).",
    )


# ---------------------------------------------------------------------------
# Challenge sub-models
# ---------------------------------------------------------------------------


class ChallengeInfo(BaseModel):
    """Challenge parameters returned inside an assess response."""

    id: str = Field(min_length=1, max_length=256, description="Single-use challenge id.")
    type: Literal["press_hold"] = Field(description="Challenge type.")
    hold_ms: int = Field(
        ge=100,
        le=10_000,
        description="Server-chosen hold duration in milliseconds (800–1500 ms).",
    )
    expires_in: int = Field(
        ge=1,
        le=3600,
        description="Seconds until the challenge expires.",
    )


# ---------------------------------------------------------------------------
# B.4 — Response: POST /v1/assess
# ---------------------------------------------------------------------------


class ModelVersions(BaseModel):
    """Version strings for loaded inference models."""

    mouse: str | None = None
    keyboard: str | None = None
    touch: str | None = None
    fusion: str | None = None


class AssessResponse(BaseModel):
    """Response from ``POST /v1/assess`` (Appendix B.4).

    The exact numeric score is **never** included; only the coarse ``band``
    is returned to untrusted callers.  The score is in logs and admin API only.
    """

    decision: Literal["allow", "challenge", "deny"] = Field(description="Access decision.")
    band: Literal["low", "medium", "high"] = Field(
        description="Risk band (coarse; the exact score is not exposed)."
    )
    token: str | None = Field(
        default=None,
        description="Signed JWT for 'allow' decisions; null when decision is 'challenge'.",
    )
    challenge: ChallengeInfo | None = Field(
        default=None,
        description="Challenge parameters when decision is 'challenge'; null otherwise.",
    )
    request_id: str = Field(description="Server-assigned request UUID.")
    model_versions: ModelVersions = Field(
        default_factory=ModelVersions,
        description="Versions of the inference models used.",
    )
    degraded: bool = Field(
        default=False,
        description="True when the decision was made in degraded mode (e.g. model unavailable).",
    )

    @model_validator(mode="after")
    def challenge_iff_challenge_decision(self) -> AssessResponse:
        if self.decision == "challenge" and self.challenge is None:
            raise ValueError("challenge object is required when decision is 'challenge'")
        if self.decision != "challenge" and self.challenge is not None:
            raise ValueError("challenge object must be null when decision is not 'challenge'")
        if self.decision == "allow" and self.token is None:
            raise ValueError("token is required when decision is 'allow'")
        return self


# ---------------------------------------------------------------------------
# Challenge assess request: POST /v1/assess/challenge
# ---------------------------------------------------------------------------


class ChallengeAssessRequest(BaseModel):
    """Request body for ``POST /v1/assess/challenge``."""

    nonce: str = Field(min_length=1, max_length=256)
    challenge_id: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=MAX_STRING_LEN)
    sdk_version: str = Field(default="unknown", max_length=MAX_STRING_LEN)
    # Interaction timing captured during the challenge.
    hold_start_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Client timestamp when the hold interaction started.",
    )
    hold_end_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Client timestamp when the hold interaction ended.",
    )
    # Optionally re-send environment for re-scoring.
    env: EnvSignals | None = None
    behaviour: BehaviourPayload | None = None


# ---------------------------------------------------------------------------
# Token verification: POST /v1/token/verify
# ---------------------------------------------------------------------------


class TokenVerifyRequest(BaseModel):
    """Request body for ``POST /v1/token/verify`` (service API key required)."""

    token: str = Field(
        min_length=1,
        max_length=4096,
        description="The JWT to verify.",
    )
    expected_action: str | None = Field(
        default=None,
        max_length=MAX_STRING_LEN,
        description="If provided, verification fails if the token's 'act' claim differs.",
    )


class TokenVerifyResponse(BaseModel):
    """Response from ``POST /v1/token/verify``."""

    valid: bool
    band: Literal["low", "medium", "high"] | None = None
    action: str | None = None
    expires_at: float | None = Field(
        default=None,
        description="Token expiry as a Unix timestamp.",
    )
    reason: str | None = Field(
        default=None,
        description="Human-readable reason when valid is False.",
    )


# ---------------------------------------------------------------------------
# Nonce response: GET /v1/nonce
# ---------------------------------------------------------------------------


class NonceResponse(BaseModel):
    """Response from ``GET /v1/nonce``."""

    nonce: str = Field(description="URL-safe, single-use 32-byte nonce.")
    expires_in: int = Field(
        ge=1,
        description="Seconds until the nonce expires.",
    )


# ---------------------------------------------------------------------------
# Health endpoint: GET /v1/health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response from ``GET /v1/health``."""

    status: Literal["ok", "degraded"] = "ok"
    model_versions: ModelVersions = Field(default_factory=ModelVersions)
    store_backend: str = Field(description="Active store backend: 'memory' or 'redis'.")
    db_ok: bool = Field(description="True when the database is reachable.")


# ---------------------------------------------------------------------------
# Error response (consistent format for all 4xx/5xx)
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Inner error object."""

    code: str = Field(
        max_length=MAX_STRING_LEN,
        description="Machine-readable error code, e.g. 'invalid_nonce'.",
    )
    message: str = Field(
        max_length=1024,
        description="Human-readable description.",
    )
    request_id: str | None = Field(
        default=None,
        description="Server request UUID for log correlation.",
    )


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all endpoints on failure."""

    error: ErrorDetail
