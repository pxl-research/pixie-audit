from __future__ import annotations

from argon2 import PasswordHasher
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import auth, settings
from app.routers import auth as auth_router
from app.routers import ui
from tests.fakes import FakeConnection, FakePool


@pytest.fixture(autouse=True)
def _configure_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_INGEST_API_KEY", "ingest-key")
    monkeypatch.setattr(settings, "AUDIT_READ_API_KEY", "read-key")
    monkeypatch.setattr(settings, "AUDIT_AUTH_USER", "audit-admin")
    monkeypatch.setattr(
        settings, "AUDIT_AUTH_PASSWORD_HASH", PasswordHasher().hash("super-secret")
    )
    monkeypatch.setattr(settings, "AUDIT_SESSION_SECRET", "session-secret")
    monkeypatch.setattr(settings, "AUDIT_SESSION_TTL_SECONDS", 1800)
    monkeypatch.setattr(settings, "AUDIT_ALLOW_UNAUTHENTICATED_READS", False)
    monkeypatch.setattr(settings, "AUDIT_SESSION_COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "AUDIT_ALLOWED_LOCATIONS", [])
    auth._failed_login_attempts.clear()


def _build_client() -> TestClient:
    app = FastAPI()
    app.state.db = FakePool(conn=FakeConnection(fetch_results=[[]]))
    app.include_router(auth_router.router)
    app.include_router(ui.router)
    return TestClient(app)


def test_login_page_is_available() -> None:
    with _build_client() as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert '<form class="card" method="post" action="/auth/login">' in response.text


def test_login_sets_session_cookie() -> None:
    with _build_client() as client:
        response = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/logs"
    set_cookie = response.headers.get("set-cookie", "")
    assert "audit_session=" in set_cookie
    assert "HttpOnly" in set_cookie


def test_login_rejects_invalid_credentials() -> None:
    with _build_client() as client:
        response = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid authentication"


def test_login_rate_limits_after_five_failures() -> None:
    with _build_client() as client:
        for _ in range(5):
            response = client.post(
                "/auth/login",
                data={"username": "audit-admin", "password": "wrong-password"},
            )
            assert response.status_code == 401

        blocked = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "wrong-password"},
        )

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "too many login attempts"


def test_auth_me_requires_session() -> None:
    with _build_client() as client:
        response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_returns_user_after_login() -> None:
    with _build_client() as client:
        login = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )
        assert login.status_code == 303

        me = client.get("/auth/me")

    assert me.status_code == 200
    assert me.json() == {"user": "audit-admin"}


def test_logout_clears_session_cookie() -> None:
    with _build_client() as client:
        login = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )
        assert login.status_code == 303

        logout = client.post("/auth/logout", follow_redirects=False)
        me = client.get("/auth/me")

    assert logout.status_code == 303
    assert logout.headers["location"] == "/login"
    assert "audit_session=" in logout.headers.get("set-cookie", "")
    assert me.status_code == 401


def test_logs_redirects_without_authentication() -> None:
    with _build_client() as client:
        response = client.get("/logs", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_logs_is_accessible_with_session_cookie() -> None:
    with _build_client() as client:
        login = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        response = client.get("/logs")

    assert response.status_code == 200
    assert "Pixie Audit" in response.text


def test_logs_embeds_configured_location_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AUDIT_ALLOWED_LOCATIONS", ["Antwerpen", "Gent"])

    with _build_client() as client:
        login = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )
        assert login.status_code == 303

        response = client.get("/logs")

    assert response.status_code == 200
    assert 'const configuredLocations = ["Antwerpen", "Gent"];' in response.text
    assert 'id="server-location-options"' in response.text


def test_logs_uses_signal_first_grouped_list_rendering() -> None:
    with _build_client() as client:
        login = client.post(
            "/auth/login",
            data={"username": "audit-admin", "password": "super-secret"},
            follow_redirects=False,
        )
        assert login.status_code == 303

        response = client.get("/logs")

    assert response.status_code == 200
    assert (
        'const RECENCY_BUCKET_ORDER = ["today", "yesterday", "last_7_days", "older"];'
        in response.text
    )
    assert 'today: "Vandaag"' in response.text
    assert 'yesterday: "Gisteren"' in response.text
    assert 'last_7_days: "Afgelopen 7 dagen"' in response.text
    assert 'older: "Ouder"' in response.text
    assert "title.textContent = view.displayTitle;" in response.text
    assert "meta.textContent = view.displayTime;" in response.text
    assert "title.textContent = conv.profile" not in response.text
    assert "id.textContent = conv.id" not in response.text
    assert "item.id.toLowerCase().includes(query)" not in response.text
    assert '(item.profile || "").toLowerCase().includes(query)' not in response.text
    assert (
        "fetch(`/conversations/${encodeURIComponent(conv.id)}/messages`)"
        in response.text
    )
    assert "| ${conv.id}" in response.text
