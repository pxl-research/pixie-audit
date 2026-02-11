from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    is_login_blocked,
    login_rate_limit_key,
    record_login_failure,
    reset_login_failures,
    session_subject_from_request,
    verify_login_credentials,
)
from app.settings import AUDIT_SESSION_COOKIE_SECURE, AUDIT_SESSION_TTL_SECONDS

router = APIRouter()


def _set_session_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=AUDIT_SESSION_TTL_SECONDS,
        httponly=True,
        secure=AUDIT_SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


@router.get("/login", response_class=HTMLResponse)
async def login_view() -> HTMLResponse:
    html = """<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pixie Audit Login</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f3ef;
      --panel: #ffffff;
      --ink: #1f1d1b;
      --muted: #6b6460;
      --accent: #c45a2a;
      --border: #e5ddd6;
      --shadow: 0 10px 30px rgba(21, 16, 12, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #fff8f0 0%, #f3efe9 40%, #efe7df 100%);
      color: var(--ink);
      padding: 16px;
    }
    .card {
      width: min(420px, 100%);
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 24px;
      display: grid;
      gap: 12px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }
    label {
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    input {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
      font-family: inherit;
      background: #fffaf6;
      width: 100%;
    }
    button {
      border: none;
      background: var(--accent);
      color: #fff;
      padding: 10px 12px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      letter-spacing: 0.02em;
    }
  </style>
</head>
<body>
  <form class="card" method="post" action="/auth/login">
    <h1>Pixie Audit</h1>
    <p>Meld je aan om auditlogs te bekijken.</p>
    <label for="username">Gebruikersnaam</label>
    <input id="username" name="username" type="text" required autocomplete="username" />
    <label for="password">Wachtwoord</label>
    <input id="password" name="password" type="password" required autocomplete="current-password" />
    <button type="submit">Aanmelden</button>
  </form>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.post("/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    key = login_rate_limit_key(request, username)
    if is_login_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts",
        )

    if not verify_login_credentials(username, password):
        record_login_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        )

    reset_login_failures(key)
    token = create_session_token(username)
    response = RedirectResponse(url="/logs", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, token)
    return response


@router.post("/auth/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/auth/me")
async def me(request: Request) -> dict[str, str]:
    subject = session_subject_from_request(request)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication",
        )
    return {"user": subject}
