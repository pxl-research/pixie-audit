from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.routers import conversations
from tests.fakes import FakeConnection, FakePool, make_request


def _conversation_row() -> dict[str, object]:
    return {
        "id": "session-123",
        "profile": "pixie-questioner",
        "started_at": datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        "ended_at": None,
        "metadata": {"location": "Antwerpen"},
    }


def test_list_conversations_applies_profile_filter_and_bounds() -> None:
    conn = FakeConnection(
        fetch_results=[
            [_conversation_row()]
        ]
    )
    request = make_request(FakePool(conn=conn))

    output = asyncio.run(
        conversations.list_conversations(
            request=request,
            profile="pixie-questioner",
            location=None,
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


def test_list_conversations_applies_location_filter_with_trimmed_value() -> None:
    conn = FakeConnection(fetch_results=[[_conversation_row()]])
    request = make_request(FakePool(conn=conn))

    output = asyncio.run(
        conversations.list_conversations(
            request=request,
            profile=None,
            location="  Antwerpen  ",
            from_ts=None,
            to_ts=None,
            limit=50,
            offset=0,
        )
    )

    assert len(output) == 1
    sql, params = conn.fetch_calls[0]
    assert "lower(trim(metadata->>'location')) = lower(trim($1))" in sql
    assert "limit $2" in sql
    assert "offset $3" in sql
    assert params == ("Antwerpen", 50, 0)


def test_list_conversations_ignores_blank_location_filter() -> None:
    conn = FakeConnection(fetch_results=[[_conversation_row()]])
    request = make_request(FakePool(conn=conn))

    asyncio.run(
        conversations.list_conversations(
            request=request,
            profile=None,
            location="   ",
            from_ts=None,
            to_ts=None,
            limit=50,
            offset=0,
        )
    )

    sql, params = conn.fetch_calls[0]
    assert "metadata->>'location'" not in sql
    assert "limit $1" in sql
    assert "offset $2" in sql
    assert params == (50, 0)


def test_list_conversations_applies_combined_filters_in_expected_order() -> None:
    conn = FakeConnection(fetch_results=[[_conversation_row()]])
    request = make_request(FakePool(conn=conn))
    from_ts = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    to_ts = datetime(2026, 2, 28, 23, 59, tzinfo=timezone.utc)

    asyncio.run(
        conversations.list_conversations(
            request=request,
            profile="pixie-questioner",
            location="Antwerpen",
            from_ts=from_ts,
            to_ts=to_ts,
            limit=42,
            offset=3,
        )
    )

    sql, params = conn.fetch_calls[0]
    assert "profile = $1" in sql
    assert "lower(trim(metadata->>'location')) = lower(trim($2))" in sql
    assert "started_at >= $3" in sql
    assert "started_at <= $4" in sql
    assert "limit $5" in sql
    assert "offset $6" in sql
    assert params == ("pixie-questioner", "Antwerpen", from_ts, to_ts, 42, 3)


def test_list_conversations_applies_from_only_filter() -> None:
    conn = FakeConnection(fetch_results=[[_conversation_row()]])
    request = make_request(FakePool(conn=conn))
    from_ts = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)

    asyncio.run(
        conversations.list_conversations(
            request=request,
            profile=None,
            location=None,
            from_ts=from_ts,
            to_ts=None,
            limit=10,
            offset=0,
        )
    )

    sql, params = conn.fetch_calls[0]
    assert "started_at >= $1" in sql
    assert "started_at <=" not in sql
    assert "limit $2" in sql
    assert "offset $3" in sql
    assert params == (from_ts, 10, 0)


def test_list_conversations_applies_to_only_filter() -> None:
    conn = FakeConnection(fetch_results=[[_conversation_row()]])
    request = make_request(FakePool(conn=conn))
    to_ts = datetime(2026, 2, 28, 23, 59, tzinfo=timezone.utc)

    asyncio.run(
        conversations.list_conversations(
            request=request,
            profile=None,
            location=None,
            from_ts=None,
            to_ts=to_ts,
            limit=10,
            offset=0,
        )
    )

    sql, params = conn.fetch_calls[0]
    assert "started_at >= " not in sql
    assert "started_at <= $1" in sql
    assert "limit $2" in sql
    assert "offset $3" in sql
    assert params == (to_ts, 10, 0)


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
