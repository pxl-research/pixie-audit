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


def _env_locations(name: str, fallback_name: str | None = None) -> list[str]:
    raw = os.getenv(name)
    if (raw is None or not raw.strip()) and fallback_name:
        raw = os.getenv(fallback_name)
    if raw is None:
        return []

    normalized_raw = raw.replace("|", ",")
    values: list[str] = []
    seen: set[str] = set()
    for token in normalized_raw.split(","):
        value = " ".join(token.split())
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(value)
    return values


AUDIT_DB_URL = os.getenv("AUDIT_DB_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
AUDIT_INGEST_API_KEY = os.getenv("AUDIT_INGEST_API_KEY") or None
AUDIT_READ_API_KEY = os.getenv("AUDIT_READ_API_KEY") or None
AUDIT_AUTH_USER = os.getenv("AUDIT_AUTH_USER") or None
AUDIT_AUTH_PASSWORD_HASH = os.getenv("AUDIT_AUTH_PASSWORD_HASH") or None
AUDIT_SESSION_SECRET = os.getenv("AUDIT_SESSION_SECRET") or None
AUDIT_SESSION_TTL_SECONDS = _env_int("AUDIT_SESSION_TTL_SECONDS", 1800)
AUDIT_SESSION_COOKIE_SECURE = _env_bool("AUDIT_SESSION_COOKIE_SECURE", True)
AUDIT_ALLOWED_LOCATIONS = _env_locations(
    "AUDIT_ALLOWED_LOCATIONS", fallback_name="ACTIVE_CLIENT_ALLOWED_LOCATIONS"
)
