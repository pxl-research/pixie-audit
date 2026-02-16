# Spec 008 - Read Detail Paginatie En Route Safety

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commit:
  - `feat(conversations): add bounded paging to messages and summaries (spec-008)`

## Implementatiebewijs

- Bounded pagination op detail-endpoints:
  - `audit-api/app/routers/conversations.py`
- Regressie- en gedragstests:
  - `audit-api/tests/test_conversations_router.py`
- API-documentatie:
  - `README.md`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Probleem
`GET /conversations/{conversation_id:path}/messages` en `/summaries` retourneren momenteel onbegrensd alle rijen.
Dat kan bij lange conversaties leiden tot trage responses en hoge memorydruk.

Daarnaast gebruikt de route `{conversation_id:path}` om slashes in IDs toe te laten. Dat is contractmatig correct, maar vraagt expliciete guardrails voor toekomstige endpointuitbreiding.

## Doel

1. Onbegrensde detail-reads vervangen door bounded queries.
2. Contractcompatibiliteit behouden voor string-based `conversation_id`, inclusief slash-gevallen.
3. Routing-risico rond `:path` expliciet maken en regressietests behouden/uitbreiden.

## Scope

- `audit-api/app/routers/conversations.py`
- `audit-api/tests/test_conversations_router.py`
- `audit-api/tests/smoke/audit_event_contract.py` (indien relevant)
- `README.md` endpointdocumentatie

## Non-Goals

1. Geen wijziging aan `audit/v1` ingest contract.
2. Geen cursor-based paginatie in deze fase.
3. Geen functionele wijziging aan role-filtering van summaries.

## Beslissingen (voorgesteld)

1. `conversation_id:path` blijft behouden om contractinvariant "string-ID" inclusief `/` te respecteren.
2. Beide detail-endpoints krijgen `limit` en `offset` queryparameters.
3. `limit` wordt server-side begrensd met vaste cap om zware queries te voorkomen.
4. Sortering blijft `created_at asc` voor stabiele chronologische weergave.

## Functionele Requirements

1. `GET /conversations/{conversation_id:path}/messages` ondersteunt:
   - `limit` (default: 200, min: 1, max: 1000)
   - `offset` (default: 0, min: 0)
2. `GET /conversations/{conversation_id:path}/summaries` ondersteunt dezelfde paging-parameters.
3. Zonder expliciete queryparameters blijven endpoints valide en voorspelbaar werken met defaultwaarden.
4. SQL blijft geparametriseerd.
5. IDs zoals `session/123` blijven ondersteund.

## Security En Performance Requirements

1. Geen onbegrensde fetches op detail-endpoints.
2. Geen SQL-stringinterpolatie met user input.
3. Paginatieparameters worden defensief begrensd in backend.

## Technisch Ontwerp (voorgesteld)

1. Voeg `limit` en `offset` toe aan router signatures.
2. Clamp `limit` en `offset` analoog aan bestaand patroon in `list_conversations`.
3. Voeg `limit/offset` toe aan SQL met placeholders.
4. Behoud `conversation_id:path` en documenteer dat extra statische routes onder `/conversations/...` zorgvuldig gekozen moeten worden.

## Teststrategie

1. Routertests voor `messages`:
   - default paging toegepast;
   - clamping van te hoge/negatieve waarden.
2. Routertests voor `summaries`:
   - role-filter blijft `summary`;
   - pagingparameters correct in SQL/params.
3. Regressietest dat `conversation_id="session/123"` blijft werken.
4. Eventuele smoke-update om detail-endpoints met `limit` te valideren.

## Acceptatiecriteria

1. Beide detail-endpoints zijn bounded via `limit/offset`.
2. String-ID met slash blijft ondersteund.
3. Geen regressie in summary-filtering of sorteervolgorde.
4. Query’s blijven geparametriseerd en testgedekt.

## Risico's

1. Te lage default `limit` kan onverwachte truncatie geven in bestaande clients.
2. Toekomstige route-uitbreidingen onder `/conversations` kunnen botsen zonder expliciete ontwerpdiscipline.

## Rollout

1. Routerwijzigingen in kleine stap.
2. Testuitbreiding op SQL + gedrag.
3. README bijwerken met nieuwe queryparams.
4. Containerized quality, tests en security gates uitvoeren.
