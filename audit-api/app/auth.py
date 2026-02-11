import logging
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Header, HTTPException, Request, status
from itsdangerous import BadData, URLSafeSerializer

from app import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "audit_session"
SESSION_SALT = "pixie-audit-session-v1"
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60

_password_hasher = PasswordHasher()
_failed_login_attempts: dict[str, deque[int]] = defaultdict(deque)


def _serializer() -> URLSafeSerializer:
    secret = settings.AUDIT_SESSION_SECRET
    if not secret:
        raise RuntimeError("AUDIT_SESSION_SECRET is required for session signing")
    return URLSafeSerializer(secret, salt=SESSION_SALT)


def _utc_now_ts() -> int:
    return int(time.time())


def _prune_attempts(bucket: deque[int], now_ts: int) -> None:
    cutoff = now_ts - LOGIN_RATE_LIMIT_WINDOW_SECONDS
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()


def login_rate_limit_key(request: Request, username: str) -> str:
    source_ip = (request.client.host if request.client else "unknown").strip()
    return f"{source_ip}:{username.strip().lower()}"


def is_login_blocked(key: str, now_ts: int | None = None) -> bool:
    now = now_ts if now_ts is not None else _utc_now_ts()
    bucket = _failed_login_attempts[key]
    _prune_attempts(bucket, now)
    return len(bucket) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS


def record_login_failure(key: str, now_ts: int | None = None) -> None:
    now = now_ts if now_ts is not None else _utc_now_ts()
    bucket = _failed_login_attempts[key]
    _prune_attempts(bucket, now)
    bucket.append(now)


def reset_login_failures(key: str) -> None:
    _failed_login_attempts.pop(key, None)


def create_session_token(subject: str, now_ts: int | None = None) -> str:
    now = now_ts if now_ts is not None else _utc_now_ts()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.AUDIT_SESSION_TTL_SECONDS,
    }
    return _serializer().dumps(payload)


def decode_session_token(token: str, now_ts: int | None = None) -> dict[str, int | str]:
    now = now_ts if now_ts is not None else _utc_now_ts()
    try:
        payload = _serializer().loads(token)
    except BadData as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        ) from exc

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        )

    sub = payload.get("sub")
    iat = payload.get("iat")
    if not isinstance(sub, str) or not sub or not isinstance(iat, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        )

    return payload


def session_subject_from_request(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        payload = decode_session_token(token)
    except HTTPException:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def verify_login_credentials(username: str, password: str) -> bool:
    expected_user = settings.AUDIT_AUTH_USER
    expected_hash = settings.AUDIT_AUTH_PASSWORD_HASH
    if not expected_user or not expected_hash:
        return False

    username_ok = secrets.compare_digest(username, expected_user)
    try:
        password_ok = _password_hasher.verify(expected_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        password_ok = False

    return username_ok and password_ok


def _header_or_request_api_key(request: Request, x_api_key: str | None) -> str | None:
    if x_api_key:
        return x_api_key
    headers = getattr(request, "headers", {}) or {}
    if isinstance(headers, dict):
        header_key = headers.get("x-api-key")
    else:
        header_key = headers.get("x-api-key")
    return header_key if header_key else None


def _request_path(request: Request) -> str:
    url = getattr(request, "url", None)
    path = getattr(url, "path", None) if url is not None else None
    return path if isinstance(path, str) else "unknown"


def _request_ip(request: Request) -> str:
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client is not None else None
    return host if isinstance(host, str) else "unknown"


def is_read_authenticated_request(
    request: Request, x_api_key: str | None = None
) -> bool:
    if settings.AUDIT_ALLOW_UNAUTHENTICATED_READS:
        return True

    read_key = settings.AUDIT_READ_API_KEY
    candidate_key = _header_or_request_api_key(request, x_api_key)
    if read_key and candidate_key and secrets.compare_digest(candidate_key, read_key):
        return True

    return session_subject_from_request(request) is not None


def require_read_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if is_read_authenticated_request(request, x_api_key=x_api_key):
        return

    logger.warning(
        "read auth rejected path=%s ip=%s",
        _request_path(request),
        _request_ip(request),
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid authentication",
    )


def require_ingest_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    ingest_key = settings.AUDIT_INGEST_API_KEY
    if ingest_key and x_api_key and secrets.compare_digest(x_api_key, ingest_key):
        return

    logger.warning(
        "ingest auth rejected path=%s ip=%s",
        _request_path(request),
        _request_ip(request),
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid authentication",
    )


def validate_auth_configuration() -> None:
    if settings.AUDIT_SESSION_TTL_SECONDS <= 0:
        raise RuntimeError("AUDIT_SESSION_TTL_SECONDS must be > 0")

    if not settings.AUDIT_INGEST_API_KEY:
        raise RuntimeError("AUDIT_INGEST_API_KEY is required")

    if settings.AUDIT_ALLOW_UNAUTHENTICATED_READS:
        return

    required = {
        "AUDIT_READ_API_KEY": settings.AUDIT_READ_API_KEY,
        "AUDIT_AUTH_USER": settings.AUDIT_AUTH_USER,
        "AUDIT_AUTH_PASSWORD_HASH": settings.AUDIT_AUTH_PASSWORD_HASH,
        "AUDIT_SESSION_SECRET": settings.AUDIT_SESSION_SECRET,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "missing required auth configuration for protected reads: "
            + ", ".join(sorted(missing))
        )
