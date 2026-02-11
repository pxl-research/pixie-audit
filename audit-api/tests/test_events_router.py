from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.routers import events
from app import settings
from app.schemas import ContractEventIn
from tests.fakes import FakeConnection, FakePool, make_request


def test_post_event_persists_conversation_and_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AUDIT_INGEST_API_KEY", "ingest-key")

    conn = FakeConnection()
    request = make_request(FakePool(conn=conn))
    event = ContractEventIn.model_validate(
        {
            "conversation_id": "session-123",
            "profile": "pixie-questioner",
            "messages": [
                {"role": "user", "content": "Ik zoek een jeans."},
                {"role": "assistant", "content": "Welke fit zoek je?"},
                {"role": "summary", "content": "Je zoekt een rechte fit."},
            ],
            "metadata": {"location": "Antwerpen"},
        }
    )

    out = asyncio.run(
        events.post_event(event=event, request=request, x_api_key="ingest-key")
    )

    assert out.status == "ok"
    assert len(conn.executed) == 4

    first_sql, first_params = conn.executed[0]
    assert "insert into audit.conversations" in first_sql
    assert first_params == (
        "session-123",
        "pixie-questioner",
        {"location": "Antwerpen"},
    )

    for sql, params in conn.executed[1:]:
        assert "insert into audit.messages" in sql
        assert params[1] == "session-123"
        assert params[2] in {"user", "assistant", "summary"}
        assert params[4] == {"location": "Antwerpen"}


def test_post_event_rejects_invalid_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUDIT_INGEST_API_KEY", "expected-key")

    conn = FakeConnection()
    request = make_request(FakePool(conn=conn))
    event = ContractEventIn.model_validate(
        {
            "conversation_id": "session-123",
            "profile": "pixie-questioner",
            "messages": [{"role": "user", "content": "Hallo"}],
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            events.post_event(
                event=event,
                request=request,
                x_api_key="wrong-key",
            )
        )

    assert exc_info.value.status_code == 401
    assert conn.executed == []
