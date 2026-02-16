# Spec 003 - Read Auth Hardening Voor Logs En Query Endpoints

## Status
Implemented

## Beslissingen

- `/logs` zonder auth redirectt naar `/login`.
- Harde key-cutover: `AUDIT_API_KEY` fallback is verwijderd.
- Sessiemodel: stateless signed cookie (`audit_session`).
- Login rate limiting: 5 mislukte pogingen per 15 minuten per `ip+username`.
- Startup policy: fail fast bij ontbrekende verplichte auth-config.

## Implementatie

- Geïmplementeerd op: 2026-02-11
- Commits:
  - `c5c460e` (`feat(auth): enforce split ingest/read auth with session login`)
  - `8b5f2ef` (`test(auth): add auth unit, route, and smoke coverage`)
  - `a3a2908` (`chore(security): add validation workflow and non-root container hardening`)

## Implementatiebewijs

- Backend auth primitives en dependencies:
  - `audit-api/app/auth.py`
  - `audit-api/app/settings.py`
  - `audit-api/app/main.py`
- Routerbescherming en auth endpoints:
  - `audit-api/app/routers/events.py`
  - `audit-api/app/routers/conversations.py`
  - `audit-api/app/routers/ui.py`
  - `audit-api/app/routers/auth.py`
- Testdekking:
  - `audit-api/tests/test_auth.py`
  - `audit-api/tests/test_auth_router.py`
  - `audit-api/tests/test_route_auth.py`
  - `audit-api/tests/test_events_router.py`
  - `audit-api/tests/smoke/audit_event_contract.py`
  - `audit-api/tests/smoke/auth_login_flow.py`
- Operationele verankering:
  - `.github/workflows/validate.yml`
  - `docs/runbooks/auth-rotation.md`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: contract + auth login flow
  - security baseline: `ruff --select S`, bandit, pip-audit
  - release scans: gitleaks en trivy

## Probleem

Vandaag zijn de read-routes publiek bereikbaar:

- `GET /logs`
- `GET /conversations`
- `GET /conversations/{id}/messages`
- `GET /conversations/{id}/summaries`

Iedereen met de URL kan dus auditdata bekijken. Omdat deze data informatie over verschillende personen kan bevatten, is dit een privacy- en securityrisico.

## Doel

- Read-toegang standaard afschermen (least privilege).
- Browsergebruik voor `/logs` veilig ondersteunen zonder secrets in URL of localStorage.
- Programmatic read access mogelijk houden voor interne tools.
- Bestaande `POST /events` contractcompatibiliteit behouden.

## Non-Goals

- Geen volledige IAM/OIDC-integratie in deze fase.
- Geen multi-tenant autorisatiemodel.
- Geen wijziging aan `audit/v1` payloadcontract.

## Threat Model

Te mitigeren risico's:

1. Ongeauthenticeerde toegang via bekende URL.
2. Credential leakage via query parameters of browseropslag.
3. Te brede sleutelrechten (zelfde key voor write + read).
4. Brute-force op login endpoint.
5. Session misbruik door zwakke cookie-instellingen.

Niet in scope (maar vereist operationeel):

1. TLS-terminatie moet correct op ingress/reverse proxy staan.
2. Netwerktoegang tot service moet beperkt zijn (private network/VPN).

## Beslissing (Voorgestelde Aanpak)

Gebruik een combinatie van:

1. Session-based auth voor browsergebruik (`/logs` en UI-fetches).
2. Dedicated read API key voor service-to-service read clients.
3. Dedicated ingest API key voor `POST /events` (split van privileges).

## Functionele Requirements

1. Read-endpoints vereisen authenticatie:
   - `GET /logs`
   - `GET /conversations`
   - `GET /conversations/{id}/messages`
   - `GET /conversations/{id}/summaries`
2. Auth is geldig als een van beide klopt:
   - geldige session cookie, of
   - correcte `X-API-Key` gelijk aan read key.
3. `POST /events` blijft key-based auth gebruiken met ingest key.
4. Login/logout endpoints:
   - `POST /auth/login`
   - `POST /auth/logout`
   - `GET /auth/me` (session check voor UI)
5. `/health` blijft zonder auth bereikbaar.

## Security Requirements

1. Geen plaintext wachtwoorden in code of repo.
2. UI login gebruikt gehashte passwordverificatie (Argon2id hash in env).
3. Session cookie-instellingen:
   - `HttpOnly`
   - `Secure` (aan in productie)
   - `SameSite=Strict`
   - beperkte `Max-Age` (bv. 30 min)
4. Brute-force baseline:
   - rate-limit login attempts per IP (app-level baseline), en
   - aanvullende rate limit op reverse proxy.
5. Auth failures loggen zonder secrets.
6. Fail-closed gedrag:
   - read auth staat altijd aan.

## Configuratie (Nieuwe Env Vars)

- `AUDIT_INGEST_API_KEY`: key voor `POST /events`.
- `AUDIT_READ_API_KEY`: key voor read API calls (niet-browser clients).
- `AUDIT_AUTH_USER`: login user voor `/logs`.
- `AUDIT_AUTH_PASSWORD_HASH`: Argon2id hash voor login verificatie.
- `AUDIT_SESSION_SECRET`: secret voor session signing.
- `AUDIT_SESSION_TTL_SECONDS`: default `1800`.
- `AUDIT_SESSION_COOKIE_SECURE`: default `true`.

## Technisch Ontwerp

### Auth module

Nieuwe module `app/auth.py` met:

1. key verificatie helpers (`_check_ingest_key`, `_check_read_key`);
2. password hash verify helper (Argon2);
3. signed session token create/verify;
4. FastAPI dependencies:
   - `require_read_auth`
   - `require_ingest_auth`

### Router integratie

1. `POST /events` gebruikt `require_ingest_auth`.
2. Conversations routers gebruiken `Depends(require_read_auth)`.
3. UI router beschermt `/logs` met `require_read_auth`.
4. Nieuwe auth router (`app/routers/auth.py`) met login/logout/me.

### Session model

Cookie naam: `audit_session`.

Inhoud (signed payload):

- `sub` (username)
- `iat`
- `exp`

Geen PII of API keys in cookie payload.

### UI flow

1. Niet-authenticeerde gebruiker op `/logs`:
   - redirect naar `/login` (nieuwe eenvoudige HTML loginpagina).
2. Login success:
   - set secure session cookie
   - redirect naar `/logs`
3. Login fail:
   - `401` met generieke foutmelding.

## Teststrategie

### Unit

1. Auth helper tests:
   - geldig/ongeldig read key
   - geldig/ongeldig ingest key
   - session sign/verify + expiry
2. Login verify met correcte/foute password hash.

### API integratie

1. `GET /conversations` zonder auth => `401`.
2. `GET /conversations` met read key => `200`.
3. `GET /logs` met geldige session => `200`.
4. `GET /logs` zonder session => redirect of `401` (volgens gekozen UX).
5. `POST /events` blijft werken met ingest key.
6. `POST /events` met enkel read key => `401`.

### Regressie

1. Bestaande contractvalidatie en adaptertests blijven groen.
2. Bestaande smoke test uitbreiden met auth flow.

## Operationele Hardening

1. Documenteer verplichte TLS in deployment.
2. Voeg voorbeeld `.env.example` entries toe zonder echte secrets.
3. Voeg runbook toe voor key/password rotatie:
   - ingest key rotatie
   - read key rotatie
   - session secret rotatie

## Acceptatiecriteria

1. Read endpoints zijn niet langer publiek toegankelijk.
2. Browser login op `/logs` werkt met session cookie.
3. Service-to-service reads werken via read API key.
4. Ingest blijft gescheiden via ingest key.
5. Containerized quality + security baseline checks zijn groen.
6. Geen secrets in code, docs of logs.

## Rollout Plan

1. Auth primitives + env/config + dependency wiring.
2. Protect read routers + add auth router/login page.
3. Tests (unit + integration + smoke auth cases).
4. Documentatie update (`README.md`, `.env.example`, `AGENTS.md` indien nodig).
5. Containerized validate + security gates.
6. Deploy met credentials geconfigureerd.

## Risico's

1. Misconfiguratie van env vars kan lockout veroorzaken.
2. Zonder TLS blijft credentialtransport kwetsbaar.
3. Single-user loginmodel is beperkt voor teams (later uit te breiden).
