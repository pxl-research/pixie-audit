from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.routers import conversations
from tests.fakes import FakeConnection, FakePool, make_request


def test_list_conversations_applies_filter_and_bounds() -> None:
    conn = FakeConnection(
        fetch_results=[
            [
                {
                    "id": "session-123",
                    "profile": "pixie-questioner",
                    "started_at": datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
                    "ended_at": None,
                    "metadata": {"location": "Antwerpen"},
                }
            ]
        ]
    )
    request = make_request(FakePool(conn=conn))

    output = asyncio.run(
        conversations.list_conversations(
            request=request,
            profile="pixie-questioner",
            from_ts=None,
            to_ts=None,
            limit=999,
            offset=-10,
        )
    )

    assert len(output) == 1
    assert output[0].id == "session-123"
    assert output[0].profile == "pixie-questioner"

    assert len(conn.fetch_calls) == 1
    sql, params = conn.fetch_calls[0]
    assert "where profile = $1" in sql
    assert "limit $2" in sql
    assert "offset $3" in sql
    assert params == ("pixie-questioner", 500, 0)


def test_list_messages_accepts_string_conversation_id() -> None:
    conn = FakeConnection(
        fetch_results=[
            [
                {
                    "id": "message-1",
                    "conversation_id": "session/123",
                    "role": "assistant",
                    "content": "Welke fit zoek je?",
                    "created_at": datetime(2026, 2, 10, 12, 1, tzinfo=timezone.utc),
                    "metadata": {"location": "Antwerpen"},
                }
            ]
        ]
    )
    request = make_request(FakePool(conn=conn))

    output = asyncio.run(
        conversations.list_messages(conversation_id="session/123", request=request)
    )

    assert len(output) == 1
    assert output[0].conversation_id == "session/123"

    sql, params = conn.fetch_calls[0]
    assert "from audit.messages" in sql
    assert params == ("session/123",)


def test_list_summaries_queries_only_summary_rows() -> None:
    conn = FakeConnection(fetch_results=[[]])
    request = make_request(FakePool(conn=conn))

    output = asyncio.run(
        conversations.list_summaries(conversation_id="session-123", request=request)
    )

    assert output == []
    sql, params = conn.fetch_calls[0]
    assert "role = 'summary'" in sql
    assert params == ("session-123",)
