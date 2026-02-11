from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def _base_url() -> str:
    return os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")


def _auth_user() -> str:
    return os.getenv("SMOKE_AUTH_USER", "audit-admin")


def _auth_password() -> str:
    return os.getenv("SMOKE_AUTH_PASSWORD", "audit-dev-password")


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor())


def _assert_logs_redirects_to_login(opener: urllib.request.OpenerDirector) -> None:
    request = urllib.request.Request(f"{_base_url()}/logs", method="GET")
    with opener.open(request, timeout=10) as response:
        final_url = response.geturl()
        assert final_url.endswith("/login"), final_url


def _assert_login_sets_session(opener: urllib.request.OpenerDirector) -> None:
    payload = urllib.parse.urlencode(
        {"username": _auth_user(), "password": _auth_password()}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{_base_url()}/auth/login",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(request, timeout=10) as response:
        final_url = response.geturl()
        assert final_url.endswith("/logs"), final_url


def _assert_me_authenticated(opener: urllib.request.OpenerDirector) -> None:
    request = urllib.request.Request(f"{_base_url()}/auth/me", method="GET")
    with opener.open(request, timeout=10) as response:
        assert response.status == 200, response.status
        body = json.loads(response.read().decode("utf-8"))
        assert body == {"user": _auth_user()}, body


def _assert_logout_invalidates_session(opener: urllib.request.OpenerDirector) -> None:
    request = urllib.request.Request(f"{_base_url()}/auth/logout", method="POST")
    with opener.open(request, timeout=10) as response:
        final_url = response.geturl()
        assert final_url.endswith("/login"), final_url

    me_request = urllib.request.Request(f"{_base_url()}/auth/me", method="GET")
    try:
        opener.open(me_request, timeout=10)
    except urllib.error.HTTPError as exc:
        assert exc.code == 401, exc.code
        body = json.loads(exc.read().decode("utf-8"))
        assert body.get("detail") == "invalid authentication", body
        return
    raise AssertionError("Expected /auth/me to require login after logout")


def main() -> None:
    opener = _opener()
    _assert_logs_redirects_to_login(opener)
    _assert_login_sets_session(opener)
    _assert_me_authenticated(opener)
    _assert_logout_invalidates_session(opener)
    print("auth login flow smoke test passed")


if __name__ == "__main__":
    main()
