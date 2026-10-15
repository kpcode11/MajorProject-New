"""HTTP request and response schemas.

Environment signal schema (Appendix B.2), behaviour payload (B.3),
assess request/response (B.4), and related models for the scoring API.

Privacy: all environment values are coarse or bucketed.  No unique
fingerprint hash is ever computed from these signals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

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
        description="Browser family in lowercase, e.g. 'chrome', 'firefox', 'safari'.",
    )
    ua_major: int | None = Field(
        default=None,
        description="Major version of the browser parsed from the UA string.",
    )
    ua_os: str | None = Field(
        default=None,
        description="OS family in lowercase, e.g. 'windows', 'macos', 'linux', 'android', 'ios'.",
    )

    # Platform and client-hints
    platform: str | None = Field(
        default=None,
        description="navigator.platform value, e.g. 'Win32', 'MacIntel', 'Linux x86_64'.",
    )
    hints_brands: list[str] | None = Field(
        default=None,
        description="Client-hints brand names, e.g. ['Chromium', 'Google Chrome'].",
    )
    hints_platform: str | None = Field(
        default=None,
        description="Client-hints platform string, e.g. 'Windows', 'macOS'.",
    )

    # Locale and timezone
    languages_count: int | None = Field(
        default=None,
        description="Length of navigator.languages.",
    )
    lang_primary: str | None = Field(
        default=None,
        description="First language tag, e.g. 'en-IN'. Used for timezone plausibility.",
    )
    timezone_offset_min: int | None = Field(
        default=None,
        description="new Date().getTimezoneOffset() in minutes (negative = east of UTC).",
    )

    # Screen and viewport (bucketed)
    screen_w_bucket: int | None = Field(
        default=None,
        description="screen.width rounded to the nearest common resolution.",
    )
    screen_h_bucket: int | None = Field(
        default=None,
        description="screen.height rounded to the nearest common resolution.",
    )
    viewport_w: int | None = Field(
        default=None,
        description="window.innerWidth in pixels.",
    )
    viewport_h: int | None = Field(
        default=None,
        description="window.innerHeight in pixels.",
    )
    outer_w: int | None = Field(
        default=None,
        description="window.outerWidth in pixels.",
    )
    outer_h: int | None = Field(
        default=None,
        description="window.outerHeight in pixels.",
    )
    dpr_bucket: float | None = Field(
        default=None,
        description="window.devicePixelRatio, bucketed (1, 1.5, 2, 3).",
    )

    # Hardware hints (bucketed)
    hw_concurrency_bucket: int | None = Field(
        default=None,
        description="navigator.hardwareConcurrency, bucketed.",
    )
    device_memory_bucket: float | None = Field(
        default=None,
        description="navigator.deviceMemory in GB, bucketed (0.25, 0.5, 1, 2, 4, 8).",
    )

    # Rendering
    webgl_renderer_class: str | None = Field(
        default=None,
        description=(
            "Classified WebGL renderer: 'hardware', 'software', 'virtual', 'unknown'."
        ),
    )

    # Browser features
    plugins_count: int | None = Field(
        default=None,
        description="navigator.plugins.length.",
    )

    # Touch capabilities
    max_touch_points: int | None = Field(
        default=None,
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
        description="document.visibilityState at collection time: 'visible', 'hidden', etc.",
    )

    def is_empty(self) -> bool:
        """Return True when every field is None (no signal provided)."""
        return all(v is None for v in self.model_dump().values())
