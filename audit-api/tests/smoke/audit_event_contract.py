from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

CONVERSATION_ID = f"session-smoke-{int(time.time())}"


def _ingest_api_key() -> str | None:
    return os.getenv("SMOKE_INGEST_API_KEY") or os.getenv("AUDIT_INGEST_API_KEY")


def _read_api_key() -> str | None:
    return os.getenv("SMOKE_READ_API_KEY") or os.getenv("AUDIT_READ_API_KEY")


def _base_headers(api_key: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _request_json(
    method: str,
    path: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    data = None
    final_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        final_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=final_headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read()
        return response.status, json.loads(body.decode("utf-8"))


def _assert_health() -> None:
    status, body = _request_json("GET", "/health")
    assert status == 200, status
    assert body == {"status": "ok"}, body


def _assert_valid_event() -> None:
    payload = {
        "conversation_id": CONVERSATION_ID,
        "profile": "pixie-questioner",
        "messages": [
            {"role": "user", "content": "Hallo"},
            {"role": "assistant", "content": "Hi"},
        ],
        "metadata": {"location": "Antwerpen"},
    }
    status, body = _request_json(
        "POST",
        "/events",
        payload,
        headers=_base_headers(_ingest_api_key()),
    )
    assert status == 200, status
    assert body == {"status": "ok"}, body


def _assert_invalid_event() -> None:
    payload = {
        "conversation_id": CONVERSATION_ID,
        "profile": "pixie-questioner",
        "messages": [{"role": "user", "content": "Hallo"}],
        "metadata": {"location": "Antwerpen", "extra": "x"},
    }
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            **_base_headers(_ingest_api_key()),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as exc:
        assert exc.code == 422, exc.code
        body = json.loads(exc.read().decode("utf-8"))
        assert "detail" in body, body
        return
    raise AssertionError("Invalid payload unexpectedly accepted")


def _assert_messages_query() -> None:
    status, body = _request_json(
        "GET",
        f"/conversations/{CONVERSATION_ID}/messages",
        headers=_base_headers(_read_api_key()),
    )
    assert status == 200, status
    assert isinstance(body, list), type(body)
    assert len(body) >= 2, body
    assert all(item.get("conversation_id") == CONVERSATION_ID for item in body), body


def _assert_conversations_location_query() -> None:
    status, body = _request_json(
        "GET",
        "/conversations?location=%20antwerpen%20&limit=200",
        headers=_base_headers(_read_api_key()),
    )
    assert status == 200, status
    assert isinstance(body, list), type(body)
    assert any(item.get("id") == CONVERSATION_ID for item in body), body


def _assert_conversations_multi_location_query() -> None:
    status, body = _request_json(
        "GET",
        "/conversations?location=gent&location=antwerpen&limit=200",
        headers=_base_headers(_read_api_key()),
    )
    assert status == 200, status
    assert isinstance(body, list), type(body)
    assert any(item.get("id") == CONVERSATION_ID for item in body), body


def _assert_conversations_date_query() -> None:
    status, body = _request_json(
        "GET",
        "/conversations?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z&limit=200",
        headers=_base_headers(_read_api_key()),
    )
    assert status == 200, status
    assert isinstance(body, list), type(body)
    assert any(item.get("id") == CONVERSATION_ID for item in body), body


def main() -> None:
    _assert_health()
    _assert_valid_event()
    _assert_invalid_event()
    _assert_conversations_location_query()
    _assert_conversations_multi_location_query()
    _assert_conversations_date_query()
    _assert_messages_query()
    print("audit event contract smoke test passed")


if __name__ == "__main__":
    main()
