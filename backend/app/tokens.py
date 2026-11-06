"""Human verification JWT issuance and single-use verification (Phase 5, P5-06).

Issued when an assessment decision is ``allow`` (or after a passed step-up
challenge). Protected portal routes and ``POST /v1/token/verify`` validate the
token and atomically consume its ``jti`` so every token is strictly single-use.

Claims (Appendix B.4):
- ``iss``  — Issuer (default ``"botguard"``)
- ``aud``  — Audience (default ``"botguard-portal"``)
- ``act``  — Protected action name (e.g. ``"otp_request"``, ``"login"``)
- ``iat``  — Issued-at Unix timestamp
- ``exp``  — Expiration Unix timestamp (default 90 s; 60–120 s range)
- ``jti``  — Single-use token identifier tracked in :class:`~app.store.Store`
- ``band`` — Coarse risk band (``"low"``, ``"medium"``, ``"high"``)

Algorithms:
- ``HS256`` — HMAC-SHA256 using ``settings.jwt_secret`` (development default).
- ``RS256`` — RSA PKCS#1 v1.5 SHA-256 via PEM key files.
- ``ES256`` — ECDSA P-256 SHA-256 via PEM key files.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import jwt
from jwt.algorithms import Algorithm, get_default_algorithms

from app.config import Settings
from app.policy import Band
from app.schemas import TokenVerifyResponse
from app.store import Store

_JTI_PREFIX = "jti:"
SUPPORTED_ALGORITHMS: frozenset[str] = frozenset({"HS256", "RS256", "ES256"})
VALID_BANDS: frozenset[str] = frozenset({"low", "medium", "high"})

# SHA-256 ASN.1 DigestInfo prefix for RFC 8017 PKCS#1 v1.5 (RS256)
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")

# NIST P-256 (secp256r1) parameters for RFC 7518 ES256
_P256_P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
_P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
_P256_A = _P256_P - 3
_P256_GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
_P256_GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5


# ---------------------------------------------------------------------------
# Pure-Python RFC 7518 RS256 & ES256 fallback when cryptography is absent
# ---------------------------------------------------------------------------


def _extract_pem_body(pem_text: str) -> tuple[str, bytes]:
    """Extract the PEM header label and base64-decoded payload bytes."""
    lines = [line.strip() for line in pem_text.strip().splitlines() if line.strip()]
    if (
        len(lines) < 2
        or not lines[0].startswith("-----BEGIN ")
        or not lines[-1].startswith("-----END ")
    ):
        raise jwt.InvalidKeyError("Expected a PEM-encoded key block")
    header = lines[0].removeprefix("-----BEGIN ").removesuffix("-----").strip()
    b64_body = "".join(lines[1:-1])
    try:
        raw = base64.b64decode(b64_body)
    except Exception as exc:
        raise jwt.InvalidKeyError(f"Invalid base64 payload in PEM key: {exc}") from exc
    return header, raw


def _parse_pem_json_key(pem_text: str, expected_alg: str) -> dict[str, Any]:
    """Parse a PEM-wrapped key dictionary used by pure-Python RS256/ES256."""
    if isinstance(pem_text, bytes):
        pem_text = pem_text.decode("utf-8")
    header, raw = _extract_pem_body(pem_text)
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise jwt.InvalidKeyError(f"Unsupported key structure in {header}: {exc}") from exc
    if not isinstance(data, dict) or data.get("alg") != expected_alg:
        raise jwt.InvalidKeyError(f"Key algorithm mismatch: expected {expected_alg}")
    data["_header"] = header
    return data


class _PurePythonRS256Algorithm(Algorithm):
    """RFC 7518 RS256 (RSA PKCS#1 v1.5 with SHA-256) using Python's built-in big-int pow."""

    def prepare_key(self, key: Any) -> dict[str, Any]:
        if isinstance(key, dict):
            return key
        if isinstance(key, (str, bytes)):
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            return _parse_pem_json_key(key_str, "RS256")
        raise jwt.InvalidKeyError("RS256 key must be a PEM string or key dict")

    def sign(self, msg: bytes, key: dict[str, Any]) -> bytes:
        if "d" not in key or "n" not in key:
            raise jwt.InvalidKeyError("RS256 signing requires a private key containing 'd' and 'n'")
        n = int(key["n"])
        d = int(key["d"])
        k_len = (n.bit_length() + 7) // 8
        digest = hashlib.sha256(msg).digest()
        t_bytes = _SHA256_DIGEST_INFO_PREFIX + digest
        ps_len = k_len - len(t_bytes) - 3
        if ps_len < 8:
            raise jwt.InvalidKeyError("RSA modulus too short for PKCS#1 v1.5 SHA-256")
        em = b"\x00\x01" + (b"\xff" * ps_len) + b"\x00" + t_bytes
        m_int = int.from_bytes(em, "big")
        s_int = pow(m_int, d, n)
        return s_int.to_bytes(k_len, "big")

    def verify(self, msg: bytes, key: dict[str, Any], sig: bytes) -> bool:
        if "n" not in key or "e" not in key:
            raise jwt.InvalidKeyError("RS256 verification requires 'n' and 'e'")
        n = int(key["n"])
        e = int(key["e"])
        k_len = (n.bit_length() + 7) // 8
        if len(sig) != k_len:
            return False
        s_int = int.from_bytes(sig, "big")
        if s_int >= n:
            return False
        m_int = pow(s_int, e, n)
        em = m_int.to_bytes(k_len, "big")
        digest = hashlib.sha256(msg).digest()
        t_bytes = _SHA256_DIGEST_INFO_PREFIX + digest
        ps_len = k_len - len(t_bytes) - 3
        expected_em = b"\x00\x01" + (b"\xff" * ps_len) + b"\x00" + t_bytes
        return hmac.compare_digest(em, expected_em)

    @staticmethod
    def to_jwk(key_obj: Any, as_dict: bool = False) -> Any:
        return {} if as_dict else "{}"

    @staticmethod
    def from_jwk(jwk: Any) -> dict[str, Any]:
        raise NotImplementedError


def _p256_add(
    p1: tuple[int, int] | None,
    p2: tuple[int, int] | None,
) -> tuple[int, int] | None:
    """Affine point addition on NIST P-256."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _P256_P == 0:
        return None
    if x1 == x2 and y1 == y2:
        lam = ((3 * x1 * x1 + _P256_A) * pow(2 * y1, _P256_P - 2, _P256_P)) % _P256_P
    else:
        lam = ((y2 - y1) * pow((x2 - x1) % _P256_P, _P256_P - 2, _P256_P)) % _P256_P
    x3 = (lam * lam - x1 - x2) % _P256_P
    y3 = (lam * (x1 - x3) - y1) % _P256_P
    return x3, y3


def _p256_mul(k: int, point: tuple[int, int]) -> tuple[int, int] | None:
    """Double-and-add scalar multiplication on NIST P-256."""
    result: tuple[int, int] | None = None
    addend: tuple[int, int] | None = point
    scalar = k % _P256_N
    while scalar > 0:
        if scalar & 1:
            result = _p256_add(result, addend)
        addend = _p256_add(addend, addend)
        scalar >>= 1
    return result


class _PurePythonES256Algorithm(Algorithm):
    """RFC 7518 ES256 (ECDSA P-256 with SHA-256, 64-byte R||S signature)."""

    def prepare_key(self, key: Any) -> dict[str, Any]:
        if isinstance(key, dict):
            return key
        if isinstance(key, (str, bytes)):
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            return _parse_pem_json_key(key_str, "ES256")
        raise jwt.InvalidKeyError("ES256 key must be a PEM string or key dict")

    def sign(self, msg: bytes, key: dict[str, Any]) -> bytes:
        if "d" not in key:
            raise jwt.InvalidKeyError("ES256 signing requires a private key containing 'd'")
        d = int(key["d"])
        z = int.from_bytes(hashlib.sha256(msg).digest(), "big")
        # Deterministic RFC 6979-style nonce from private scalar + message hash
        k_seed = hmac.new(
            d.to_bytes(32, "big"),
            hashlib.sha256(msg).digest(),
            hashlib.sha256,
        ).digest()
        k = (int.from_bytes(k_seed, "big") % (_P256_N - 1)) + 1
        pt = _p256_mul(k, (_P256_GX, _P256_GY))
        assert pt is not None
        r = pt[0] % _P256_N
        s = (pow(k, _P256_N - 2, _P256_N) * (z + r * d)) % _P256_N
        if s > _P256_N // 2:
            s = _P256_N - s
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    def verify(self, msg: bytes, key: dict[str, Any], sig: bytes) -> bool:
        if "qx" not in key or "qy" not in key:
            raise jwt.InvalidKeyError("ES256 verification requires 'qx' and 'qy'")
        if len(sig) != 64:
            return False
        r = int.from_bytes(sig[:32], "big")
        s = int.from_bytes(sig[32:], "big")
        if not (1 <= r < _P256_N and 1 <= s < _P256_N):
            return False
        z = int.from_bytes(hashlib.sha256(msg).digest(), "big")
        w = pow(s, _P256_N - 2, _P256_N)
        u1 = (z * w) % _P256_N
        u2 = (r * w) % _P256_N
        q_pt = (int(key["qx"]), int(key["qy"]))
        p1 = _p256_mul(u1, (_P256_GX, _P256_GY))
        p2 = _p256_mul(u2, q_pt)
        pt = _p256_add(p1, p2)
        if pt is None:
            return False
        return (pt[0] % _P256_N) == r

    @staticmethod
    def to_jwk(key_obj: Any, as_dict: bool = False) -> Any:
        return {} if as_dict else "{}"

    @staticmethod
    def from_jwk(jwk: Any) -> dict[str, Any]:
        raise NotImplementedError


def _ensure_asymmetric_algorithms_registered() -> None:
    """Register pure-Python RS256 and ES256 if PyJWT was installed without cryptography."""
    default_algs = get_default_algorithms()
    if "RS256" not in default_algs:
        jwt.register_algorithm("RS256", _PurePythonRS256Algorithm())
    if "ES256" not in default_algs:
        jwt.register_algorithm("ES256", _PurePythonES256Algorithm())


_ensure_asymmetric_algorithms_registered()


# ---------------------------------------------------------------------------
# Key-Pair Generation Helper (for dev, tests, and local staging)
# ---------------------------------------------------------------------------

# Proven Mersenne primes M_521 and M_607 for deterministic 1128-bit RSA keypair generation
_TEST_RSA_P = (1 << 521) - 1
_TEST_RSA_Q = (1 << 607) - 1


def generate_pem_keypair(algorithm: Literal["RS256", "ES256"] = "RS256") -> tuple[str, str]:
    """Return a ``(private_pem, public_pem)`` pair for ``RS256`` or ``ES256``."""
    if algorithm == "RS256":
        n = _TEST_RSA_P * _TEST_RSA_Q
        phi = (_TEST_RSA_P - 1) * (_TEST_RSA_Q - 1)
        e = 65537
        d = pow(e, -1, phi)
        priv_payload = base64.b64encode(
            json.dumps({"alg": "RS256", "n": n, "e": e, "d": d}).encode("utf-8")
        ).decode("ascii")
        pub_payload = base64.b64encode(
            json.dumps({"alg": "RS256", "n": n, "e": e}).encode("utf-8")
        ).decode("ascii")
        return (
            f"-----BEGIN RSA PRIVATE KEY-----\n{priv_payload}\n-----END RSA PRIVATE KEY-----\n",
            f"-----BEGIN PUBLIC KEY-----\n{pub_payload}\n-----END PUBLIC KEY-----\n",
        )
    if algorithm == "ES256":
        seed_int = int.from_bytes(hashlib.sha256(b"botguard-es256-key").digest(), "big")
        d = (seed_int % (_P256_N - 1)) + 1
        pub_pt = _p256_mul(d, (_P256_GX, _P256_GY))
        assert pub_pt is not None
        qx, qy = pub_pt
        priv_payload = base64.b64encode(
            json.dumps({"alg": "ES256", "d": d, "qx": qx, "qy": qy}).encode("utf-8")
        ).decode("ascii")
        pub_payload = base64.b64encode(
            json.dumps({"alg": "ES256", "qx": qx, "qy": qy}).encode("utf-8")
        ).decode("ascii")
        return (
            f"-----BEGIN EC PRIVATE KEY-----\n{priv_payload}\n-----END EC PRIVATE KEY-----\n",
            f"-----BEGIN PUBLIC KEY-----\n{pub_payload}\n-----END PUBLIC KEY-----\n",
        )
    raise ValueError(f"Unsupported keypair algorithm: {algorithm!r}")


# ---------------------------------------------------------------------------
# Data Structures & Exceptions
# ---------------------------------------------------------------------------


class TokenError(Exception):
    """Raised when a JWT fails verification or single-use JTI checks."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


@dataclass(frozen=True)
class TokenClaims:
    """Validated claims extracted from a verified human token."""

    iss: str
    aud: str
    act: str
    iat: float
    exp: float
    jti: str
    band: Band


# ---------------------------------------------------------------------------
# Key Resolution
# ---------------------------------------------------------------------------


def _signing_key(settings: Settings) -> str:
    """Return the signing key configured in ``settings``."""
    alg = settings.jwt_algorithm.upper()
    if alg not in SUPPORTED_ALGORITHMS:
        raise TokenError("unsupported_algorithm", f"Unsupported JWT algorithm: {alg}")
    if alg == "HS256":
        if not settings.jwt_secret:
            raise TokenError("missing_signing_key", "JWT_SECRET must not be empty for HS256")
        return settings.jwt_secret
    priv_pem = settings.jwt_private_key()
    if not priv_pem:
        raise TokenError(
            "missing_signing_key",
            f"JWT_PRIVATE_KEY_FILE must be configured for {alg}",
        )
    return priv_pem


def _verification_key(settings: Settings) -> str:
    """Return the verification key configured in ``settings``."""
    alg = settings.jwt_algorithm.upper()
    if alg not in SUPPORTED_ALGORITHMS:
        raise TokenError("unsupported_algorithm", f"Unsupported JWT algorithm: {alg}")
    if alg == "HS256":
        if not settings.jwt_secret:
            raise TokenError("missing_verification_key", "JWT_SECRET must not be empty for HS256")
        return settings.jwt_secret
    pub_pem = settings.jwt_public_key()
    if pub_pem:
        return pub_pem
    priv_pem = settings.jwt_private_key()
    if priv_pem:
        return priv_pem
    raise TokenError(
        "missing_verification_key",
        f"JWT_PUBLIC_KEY_FILE or JWT_PRIVATE_KEY_FILE must be configured for {alg}",
    )


# ---------------------------------------------------------------------------
# Token Issuance & Verification
# ---------------------------------------------------------------------------


def issue_token(
    store: Store,
    settings: Settings,
    *,
    action: str,
    band: Band,
    ttl: int | None = None,
    now: float | None = None,
) -> str:
    """Issue a signed JWT with single-use ``jti`` stored in ``store``.

    Args:
        store: Backing :class:`~app.store.Store` for single-use ``jti`` tracking.
        settings: Application :class:`~app.config.Settings`.
        action: Protected action identifier (``act`` claim).
        band: Risk band (``"low"``, ``"medium"``, ``"high"``).
        ttl: Optional token lifetime override in seconds (defaults to
            ``settings.jwt_expire_seconds``).
        now: Optional Unix timestamp override for deterministic tests.

    Returns:
        Encoded JWT string.
    """
    if not action or not action.strip():
        raise ValueError("action must be a non-empty string")
    if band not in VALID_BANDS:
        raise ValueError(f"band must be one of {sorted(VALID_BANDS)}, got {band!r}")

    expire_s = int(ttl if ttl is not None else settings.jwt_expire_seconds)
    if expire_s <= 0:
        raise ValueError(f"token ttl must be positive, got {expire_s}")

    issued_at = float(now if now is not None else time.time())
    expires_at = issued_at + float(expire_s)
    jti = secrets.token_urlsafe(24)

    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "act": action,
        "iat": issued_at,
        "exp": expires_at,
        "jti": jti,
        "band": band,
    }

    key = _signing_key(settings)
    alg = settings.jwt_algorithm.upper()
    encoded = jwt.encode(payload, key, algorithm=alg)

    # Record single-use JTI in store with matching TTL
    store.set(f"{_JTI_PREFIX}{jti}", action, ttl=expire_s)
    return encoded


def verify_token(
    store: Store,
    settings: Settings,
    token: str,
    *,
    expected_action: str | None = None,
    consume: bool = True,
) -> TokenClaims:
    """Verify a JWT's signature, expiry, action claim, and single-use ``jti``.

    Args:
        store: Backing :class:`~app.store.Store` used to atomically consume ``jti``.
        settings: Application :class:`~app.config.Settings`.
        token: Encoded JWT string.
        expected_action: Optional action name that must match the ``act`` claim.
        consume: When ``True`` (default), atomically consumes the ``jti`` via
            ``store.get_and_delete`` so any replay is rejected.

    Returns:
        Validated :class:`TokenClaims`.

    Raises:
        TokenError: With a machine-readable ``code`` on any validation failure.
    """
    if not token or not isinstance(token, str):
        raise TokenError("missing_token", "Token must be a non-empty string")

    alg = settings.jwt_algorithm.upper()
    key = _verification_key(settings)

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise TokenError("malformed_token", f"Invalid JWT header: {exc}") from exc

    header_alg = str(unverified_header.get("alg", "")).upper()
    if header_alg != alg:
        raise TokenError(
            "invalid_algorithm",
            f"Token algorithm {header_alg!r} does not match expected {alg!r}",
        )

    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[alg],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": ["iss", "aud", "act", "iat", "exp", "jti", "band"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token_expired", "Token has expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise TokenError("invalid_issuer", "Token issuer mismatch") from exc
    except jwt.InvalidAudienceError as exc:
        raise TokenError("invalid_audience", "Token audience mismatch") from exc
    except jwt.MissingRequiredClaimError as exc:
        raise TokenError("missing_claim", f"Token missing required claim: {exc}") from exc
    except jwt.InvalidSignatureError as exc:
        raise TokenError("invalid_signature", "Token signature verification failed") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("invalid_token", f"Token validation failed: {exc}") from exc

    act = str(decoded.get("act", ""))
    jti = str(decoded.get("jti", ""))
    band_raw = str(decoded.get("band", ""))
    if not act or not jti or band_raw not in VALID_BANDS:
        raise TokenError("invalid_claims", "Token contains invalid act, jti, or band claim")

    if expected_action is not None and act != expected_action:
        raise TokenError(
            "action_mismatch",
            f"Token action {act!r} does not match expected action {expected_action!r}",
        )

    if consume:
        stored_act = store.get_and_delete(f"{_JTI_PREFIX}{jti}")
        if stored_act is None:
            raise TokenError(
                "token_replayed_or_revoked",
                "Token JTI has already been consumed or expired",
            )
    else:
        if store.get(f"{_JTI_PREFIX}{jti}") is None:
            raise TokenError(
                "token_replayed_or_revoked",
                "Token JTI has already been consumed or expired",
            )

    return TokenClaims(
        iss=str(decoded["iss"]),
        aud=str(decoded["aud"]),
        act=act,
        iat=float(decoded["iat"]),
        exp=float(decoded["exp"]),
        jti=jti,
        band=band_raw,  # type: ignore[arg-type]
    )


def verify_token_response(
    store: Store,
    settings: Settings,
    token: str,
    *,
    expected_action: str | None = None,
    consume: bool = True,
) -> TokenVerifyResponse:
    """Verify a token and return a :class:`~app.schemas.TokenVerifyResponse`."""
    try:
        claims = verify_token(
            store,
            settings,
            token,
            expected_action=expected_action,
            consume=consume,
        )
        return TokenVerifyResponse(
            valid=True,
            band=claims.band,
            action=claims.act,
            expires_at=claims.exp,
            reason=None,
        )
    except TokenError as exc:
        return TokenVerifyResponse(
            valid=False,
            band=None,
            action=None,
            expires_at=None,
            reason=exc.code,
        )


def write_keypair_files(
    directory: Path,
    *,
    algorithm: Literal["RS256", "ES256"] = "RS256",
) -> tuple[Path, Path]:
    """Write ``private.pem`` and ``public.pem`` files into ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    priv_pem, pub_pem = generate_pem_keypair(algorithm)
    priv_path = directory / f"{algorithm.lower()}_private.pem"
    pub_path = directory / f"{algorithm.lower()}_public.pem"
    priv_path.write_text(priv_pem, encoding="utf-8")
    pub_path.write_text(pub_pem, encoding="utf-8")
    return priv_path, pub_path
