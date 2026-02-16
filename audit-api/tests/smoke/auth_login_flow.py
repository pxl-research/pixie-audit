from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


def _base_url() -> str:
    return os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")


def _running_in_ci() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes"}


def _require_smoke_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required when running auth smoke in CI")
    return value


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor())


def _assert_logs_redirects_to_login(opener: urllib.request.OpenerDirector) -> None:
    request = urllib.request.Request(f"{_base_url()}/logs", method="GET")
    with opener.open(request, timeout=10) as response:
        final_url = response.geturl()
        assert final_url.endswith("/login"), final_url


def _assert_login_sets_session(
    opener: urllib.request.OpenerDirector, username: str, password: str
) -> None:
    payload = urllib.parse.urlencode(
        {"username": username, "password": password}
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


def _assert_me_authenticated(
    opener: urllib.request.OpenerDirector, expected_user: str
) -> None:
    request = urllib.request.Request(f"{_base_url()}/auth/me", method="GET")
    with opener.open(request, timeout=10) as response:
        assert response.status == 200, response.status
        body = json.loads(response.read().decode("utf-8"))
        assert body == {"user": expected_user}, body


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
    if not _running_in_ci():
        print("auth login flow smoke test skipped outside CI")
        return

    smoke_user = _require_smoke_env("SMOKE_AUTH_USER")
    smoke_password = _require_smoke_env("SMOKE_AUTH_PASSWORD")

    opener = _opener()
    _assert_logs_redirects_to_login(opener)
    _assert_login_sets_session(opener, username=smoke_user, password=smoke_password)
    _assert_me_authenticated(opener, expected_user=smoke_user)
    _assert_logout_invalidates_session(opener)
    print("auth login flow smoke test passed")


if __name__ == "__main__":
    main()
