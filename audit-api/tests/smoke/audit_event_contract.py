from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def _api_key() -> str | None:
    return os.getenv("SMOKE_API_KEY") or os.getenv("AUDIT_API_KEY")


def _base_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = _api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _request_json(
    method: str, path: str, payload: dict | None = None
) -> tuple[int, dict]:
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    data = None
    headers = _base_headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
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
        "conversation_id": "session-smoke",
        "profile": "pixie-questioner",
        "messages": [
            {"role": "user", "content": "Hallo"},
            {"role": "assistant", "content": "Hi"},
        ],
    }
    status, body = _request_json("POST", "/events", payload)
    assert status == 200, status
    assert body == {"status": "ok"}, body


def _assert_invalid_event() -> None:
    payload = {
        "conversation_id": "session-smoke",
        "profile": "pixie-questioner",
        "messages": [{"role": "user", "content": "Hallo"}],
        "metadata": {"location": "Antwerpen", "extra": "x"},
    }
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={**_base_headers(), "Content-Type": "application/json"},
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
    status, body = _request_json("GET", "/conversations/session-smoke/messages")
    assert status == 200, status
    assert isinstance(body, list), type(body)
    assert len(body) >= 2, body
    assert all(item.get("conversation_id") == "session-smoke" for item in body), body


def main() -> None:
    _assert_health()
    _assert_valid_event()
    _assert_invalid_event()
    _assert_messages_query()
    print("audit event contract smoke test passed")


if __name__ == "__main__":
    main()
