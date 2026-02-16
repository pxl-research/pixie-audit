from __future__ import annotations

from argon2 import PasswordHasher
import pytest
from fastapi import HTTPException

from app import auth, settings


def _set_default_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_INGEST_API_KEY", "ingest-key")
    monkeypatch.setattr(settings, "AUDIT_READ_API_KEY", "read-key")
    monkeypatch.setattr(settings, "AUDIT_AUTH_USER", "audit-admin")
    monkeypatch.setattr(
        settings, "AUDIT_AUTH_PASSWORD_HASH", PasswordHasher().hash("super-secret")
    )
    monkeypatch.setattr(settings, "AUDIT_SESSION_SECRET", "session-secret")
    monkeypatch.setattr(settings, "AUDIT_SESSION_TTL_SECONDS", 1800)
    monkeypatch.setattr(settings, "AUDIT_SESSION_COOKIE_SECURE", True)


def test_session_token_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_SESSION_SECRET", "session-secret")
    monkeypatch.setattr(settings, "AUDIT_SESSION_TTL_SECONDS", 1800)

    token = auth.create_session_token("audit-admin", now_ts=1_000_000)
    payload = auth.decode_session_token(token, now_ts=1_000_100)

    assert payload["sub"] == "audit-admin"
    assert payload["iat"] == 1_000_000
    assert payload["exp"] == 1_001_800


def test_session_token_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_SESSION_SECRET", "session-secret")
    monkeypatch.setattr(settings, "AUDIT_SESSION_TTL_SECONDS", 10)
    token = auth.create_session_token("audit-admin", now_ts=100)

    with pytest.raises(HTTPException) as exc_info:
        auth.decode_session_token(token, now_ts=111)

    assert exc_info.value.status_code == 401


def test_verify_login_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_AUTH_USER", "audit-admin")
    monkeypatch.setattr(
        settings, "AUDIT_AUTH_PASSWORD_HASH", PasswordHasher().hash("super-secret")
    )

    assert auth.verify_login_credentials("audit-admin", "super-secret")
    assert not auth.verify_login_credentials("audit-admin", "wrong-secret")
    assert not auth.verify_login_credentials("other-user", "super-secret")


def test_rate_limiter_blocks_after_five_failures() -> None:
    auth._failed_login_attempts.clear()
    key = "127.0.0.1:audit-admin"
    for attempt in range(5):
        auth.record_login_failure(key, now_ts=100 + attempt)

    assert auth.is_login_blocked(key, now_ts=104)
    auth.reset_login_failures(key)
    assert not auth.is_login_blocked(key, now_ts=104)


def test_rate_limiter_window_expires_attempts() -> None:
    auth._failed_login_attempts.clear()
    key = "127.0.0.1:audit-admin"
    for _ in range(5):
        auth.record_login_failure(key, now_ts=100)

    assert auth.is_login_blocked(key, now_ts=100)
    assert not auth.is_login_blocked(
        key, now_ts=100 + auth.LOGIN_RATE_LIMIT_WINDOW_SECONDS + 1
    )


def test_validate_auth_configuration_rejects_missing_ingest_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_default_auth_env(monkeypatch)
    monkeypatch.setattr(settings, "AUDIT_INGEST_API_KEY", None)

    with pytest.raises(RuntimeError, match="AUDIT_INGEST_API_KEY is required"):
        auth.validate_auth_configuration()


def test_validate_auth_configuration_requires_read_auth_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_default_auth_env(monkeypatch)
    monkeypatch.setattr(settings, "AUDIT_READ_API_KEY", None)

    with pytest.raises(RuntimeError, match="missing required auth configuration"):
        auth.validate_auth_configuration()
