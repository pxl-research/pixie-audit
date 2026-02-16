# Spec 007 - Ingest Auth Dependency Consistentie

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commit:
  - `feat(auth): enforce ingest dependency and simplify api-key extraction (spec-007)`

## Implementatiebewijs

- Ingest auth dependency-wiring:
  - `audit-api/app/routers/events.py`
- Vereenvoudigde API-key header fallback:
  - `audit-api/app/auth.py`
- Testdekking en regressies:
  - `audit-api/tests/test_events_router.py`
  - `audit-api/tests/test_route_auth.py`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Probleem
`POST /events` roept `require_ingest_auth(...)` momenteel handmatig aan in de route-body.
Dat is inconsistent met read-routes die dependency-based beveiligd zijn en verhoogt het risico dat een nieuwe ingest-route auth vergeet toe te passen.

Daarnaast bevat `_header_or_request_api_key` redundante logica, waardoor auth-code minder helder is dan nodig.

## Doel

1. Ingest-auth afdwingen via FastAPI dependency-mechanisme in plaats van handmatige routecode.
2. Auth-helperlogica vereenvoudigen zonder gedragswijziging in read-auth checks.
3. Testen op HTTP-routegedrag als bron van waarheid voor auth enforcement.

## Scope

- `audit-api/app/routers/events.py`
- `audit-api/app/auth.py`
- relevante auth/router tests in `audit-api/tests/`

## Non-Goals

1. Geen wijziging aan ingest/read key-model.
2. Geen wijziging aan `POST /events` payloadcontract.
3. Geen wijziging aan sessie-auth flow.

## Functionele Requirements

1. `POST /events` moet ingest-auth krijgen via `Depends(require_ingest_auth)` (route- of router-level).
2. Handmatige route-call naar `require_ingest_auth(...)` wordt verwijderd.
3. Een ontbrekende/foute ingest key blijft `401` geven.
4. Een geldige ingest key blijft `200` geven met ongewijzigde response (`{"status": "ok"}`).

## Security Requirements

1. Geen bypasspad voor ingest-auth door route-implementatie.
2. Logging van auth-failures blijft zonder secrets.
3. Read key mag ingest nooit autoriseren.

## Technisch Ontwerp (voorgesteld)

### Router wiring

1. Voeg ingest-auth dependency toe op route-niveau of router-niveau in `events.py`.
2. Verwijder routeparameter `x_api_key` uit handler als deze niet meer nodig is in de route-body.

### Helper cleanup

1. Vereenvoudig `_header_or_request_api_key` naar eenduidige fallback:
   - eerst expliciete dependency-header (`x_api_key`);
   - anders `request.headers.get("x-api-key")`.
2. Verwijder redundante `isinstance(..., dict)` takken.

## Teststrategie

1. Route-auth tests blijven `401` valideren voor:
   - ontbrekende key;
   - foutieve key;
   - read key op ingest endpoint.
2. Route-auth tests blijven `200` valideren voor geldige ingest key.
3. Minstens één test moet endpoint via HTTP-client aanroepen zodat dependency-executie effectief wordt gevalideerd.
4. Regressietests voor read-auth blijven groen.

## Acceptatiecriteria

1. Ingest-auth wordt niet meer handmatig vanuit route-body aangeroepen.
2. Auth-gedrag op `POST /events` blijft functioneel identiek.
3. Auth-helper is eenvoudiger en zonder dode/duplicatieve paden.
4. Relevante tests dekken dependency-gedrag expliciet.

## Risico's

1. Bestaande unit-tests die routefuncties direct oproepen kunnen dependency-gedrag niet afdekken.
2. Onzorgvuldige refactor kan per ongeluk signature/typing regressie introduceren.

## Rollout

1. Dependency wiring aanpassen.
2. Helper vereenvoudigen.
3. Router/auth tests updaten.
4. Containerized quality, tests en relevante security gates uitvoeren.
