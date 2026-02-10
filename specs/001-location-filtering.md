# Spec 001 - Location In Audit Logs Opslaan En Filteren

## Status
Implemented

## Probleem
De audit events kunnen `metadata.location` bevatten, maar location is nog geen expliciete filter op de audit views/API.
Daardoor kunnen gebruikers niet gericht zoeken op locatie in logs.

## Implementatie

- Geïmplementeerd op: 2026-02-10
- Commits:
  - `fd621b4` (`feat(conversations): add normalized location filter and indexing`)
  - `2aa2fb6` (`feat(ui): add server-side log filters for location and datetime`)
  - `a66435d` (`test(smoke): verify location and date conversation filters`)

## Implementatiebewijs

- Backend filter:
  - `audit-api/app/routers/conversations.py`
- DB index (nieuw + bestaande volumes):
  - `audit-db/init.sql`
  - `audit-api/app/db.py`
- UI filter:
  - `audit-api/app/routers/ui.py`
- Testdekking:
  - `audit-api/tests/test_conversations_router.py`
  - `audit-api/tests/smoke/audit_event_contract.py`
- Containerized checks uitgevoerd en groen:
  - compileall, black, ruff, ty, pytest, smoke
  - security baseline: `ruff --select S`, bandit, pip-audit

## Doel

- Location uit inkomende audit events betrouwbaar opslaan.
- Location als eerste-klas filter ondersteunen op `GET /conversations`.
- Location filter beschikbaar maken in `/logs` UI.
- Filtering performant houden bij grotere datasets.

## Non-Goals

- Geen wijziging aan `pixie-contracts` audit/v1 payloadvorm.
- Geen geavanceerde geospatiale zoekfunctionaliteit.
- Geen retroactieve datacorrectie op historisch inconsistente location-waarden.

## Huidige Situatie

- `POST /events` accepteert contractmetadata met `location`.
- Metadata wordt opgeslagen in `audit.conversations.metadata` (jsonb) en `audit.messages.metadata` (jsonb).
- `GET /conversations` ondersteunt al `profile`, `from`, `to`, `limit`, `offset`, maar geen `location`.

## Functionele Requirements

1. `GET /conversations` accepteert queryparameter `location`.
2. Filter matcht exact op genormaliseerde string (`trim`), case-insensitive vergelijking.
3. Als `location` leeg of whitespace is, wordt de filter genegeerd.
4. Resultaten blijven gesorteerd op `started_at desc`.
5. Combineerbaar met bestaande filters (`profile`, `from`, `to`).
6. `/logs` UI krijgt een apart invoerveld voor `location`.
7. UI verstuurt `location` queryparameter naar backend.

## Niet-Functionele Requirements

1. Filterquery moet schaalbaar zijn (indexstrategie nodig).
2. Geen regressie op bestaande queryfunctionaliteit.
3. Contractcompatibiliteit met `audit/v1` blijft behouden.

## Technisch Ontwerp

### API

- Endpoint: `GET /conversations`
- Nieuwe queryparam:
  - `location: str | None`
- SQL-filter:
  - `lower(trim(metadata->>'location')) = lower(trim($N))`

### Data-opslag

- Bestaande opslag in jsonb blijft behouden.
- Geen payloadcontract-wijziging nodig.

### Indexering

- Voeg expressie-index toe op conversations voor location-filter:
  - `create index ... on audit.conversations ((lower(trim(metadata->>'location'))));`
- Index via `init.sql` voor nieuwe databases.
- Voor bestaande databases:
  - runtime `create index if not exists ...` tijdens startup, of expliciete migratiestap.

### UI

- In `/logs`:
  - extra inputveld `location`.
  - opnemen in fetch URL (`/conversations?...&location=...`).
  - behouden van bestaande tekstfilter op client-side lijstweergave.

## Teststrategie

### Unit/API

1. Nieuwe routertest: filter op `location` bouwt correcte SQL en params.
2. Combinatietest: `profile + location + date` samen.
3. Validatie dat lege/whitespace location genegeerd wordt.

### Smoke

1. Smoke payload met `metadata.location`.
2. Follow-up check dat `GET /conversations?location=...` de juiste conversatie bevat.

### Regressie

1. Bestaande tests voor events en conversation-list blijven groen.

## Acceptatiecriteria

1. `GET /conversations?location=antwerpen` filtert correct case-insensitive.
2. `/logs` laat location filteren zonder handmatige URL-edit.
3. Baseline checks (black, ruff, ty, pytest, smoke, security-baseline) zijn groen in containerized run.
4. Geen breaking change op bestaand audit/v1 contract.

## Risico's

- Inconsistente input (spaties/casing) kan filtering beïnvloeden zonder normalisatie.
- JSON-expressiefilter zonder index geeft performantieproblemen op grote tabellen.

## Rollout

1. Backend filtering + tests.
2. Index migratie.
3. UI filterveld.
4. Smoke update en finale baseline-checks.
