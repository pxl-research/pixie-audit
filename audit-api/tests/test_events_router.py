from __future__ import annotations

import asyncio

from app.routers import events
from app.schemas import ContractEventIn
from tests.fakes import FakeConnection, FakePool, make_request


def test_post_event_persists_conversation_and_messages() -> None:
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

    out = asyncio.run(events.post_event(event=event, request=request))

    assert out.status == "ok"
    assert len(conn.executed) == 4

    first_sql, first_params = conn.executed[0]
    assert "insert into audit.conversations" in first_sql
    assert "on conflict (id) do nothing" in first_sql
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
