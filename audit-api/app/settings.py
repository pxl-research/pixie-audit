import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


AUDIT_DB_URL = os.getenv("AUDIT_DB_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
AUDIT_INGEST_API_KEY = os.getenv("AUDIT_INGEST_API_KEY") or None
AUDIT_READ_API_KEY = os.getenv("AUDIT_READ_API_KEY") or None
AUDIT_AUTH_USER = os.getenv("AUDIT_AUTH_USER") or None
AUDIT_AUTH_PASSWORD_HASH = os.getenv("AUDIT_AUTH_PASSWORD_HASH") or None
AUDIT_SESSION_SECRET = os.getenv("AUDIT_SESSION_SECRET") or None
AUDIT_SESSION_TTL_SECONDS = _env_int("AUDIT_SESSION_TTL_SECONDS", 1800)
AUDIT_ALLOW_UNAUTHENTICATED_READS = _env_bool(
    "AUDIT_ALLOW_UNAUTHENTICATED_READS", False
)
AUDIT_SESSION_COOKIE_SECURE = _env_bool("AUDIT_SESSION_COOKIE_SECURE", True)
