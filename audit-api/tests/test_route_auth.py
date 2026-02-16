from __future__ import annotations

from argon2 import PasswordHasher
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import auth, settings
from app.routers import conversations, events, exports
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
    auth._failed_login_attempts.clear()


def _build_client(
    fetch_results: list[list[dict[str, object]]] | None = None,
) -> TestClient:
    app = FastAPI()
    app.state.db = FakePool(conn=FakeConnection(fetch_results=fetch_results or []))
    app.include_router(events.router)
    app.include_router(conversations.router)
    app.include_router(exports.router)
    return TestClient(app)


def test_conversations_requires_auth() -> None:
    with _build_client(fetch_results=[[]]) as client:
        response = client.get("/conversations")

    assert response.status_code == 401


def test_conversations_accepts_read_api_key() -> None:
    rows = [
        {
            "id": "session-1",
            "profile": "pixie-questioner",
            "started_at": datetime(2026, 2, 11, 9, 0, tzinfo=timezone.utc),
            "ended_at": None,
            "metadata": {"location": "Antwerpen"},
        }
    ]
    with _build_client(fetch_results=[[rows[0]]]) as client:
        response = client.get("/conversations", headers={"X-API-Key": "read-key"})

    assert response.status_code == 200
    assert response.json()[0]["id"] == "session-1"


def test_messages_requires_auth() -> None:
    with _build_client(fetch_results=[[]]) as client:
        response = client.get("/conversations/session-1/messages")

    assert response.status_code == 401


def test_summaries_requires_auth() -> None:
    with _build_client(fetch_results=[[]]) as client:
        response = client.get("/conversations/session-1/summaries")

    assert response.status_code == 401


def test_exports_requires_auth() -> None:
    with _build_client(fetch_results=[[]]) as client:
        response = client.get("/exports/logs.xlsx")

    assert response.status_code == 401


def test_exports_accepts_read_api_key() -> None:
    with _build_client(fetch_results=[[]]) as client:
        response = client.get("/exports/logs.xlsx", headers={"X-API-Key": "read-key"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=" in response.headers["content-disposition"]


def test_events_rejects_read_key() -> None:
    payload = {
        "conversation_id": "session-123",
        "profile": "pixie-questioner",
        "messages": [{"role": "user", "content": "Hallo"}],
    }
    with _build_client() as client:
        response = client.post(
            "/events", json=payload, headers={"X-API-Key": "read-key"}
        )

    assert response.status_code == 401


def test_events_accepts_ingest_key() -> None:
    payload = {
        "conversation_id": "session-123",
        "profile": "pixie-questioner",
        "messages": [{"role": "user", "content": "Hallo"}],
    }
    with _build_client() as client:
        response = client.post(
            "/events",
            json=payload,
            headers={"X-API-Key": "ingest-key"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
