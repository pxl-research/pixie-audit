# Spec 006 - Audit Follow-Up Triage En Scope

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commit:
  - `docs(spec-006): finalize audit follow-up triage scope`

## Implementatiebewijs

- Triage en scope-afbakening:
  - `specs/006-audit-follow-up-triage.md`
- Doorvertaling naar uitvoerbare opvolgspecs:
  - `specs/007-ingest-auth-dependency-consistency.md`
  - `specs/008-read-detail-pagination-and-route-safety.md`
  - `specs/009-login-rate-limit-scaling-and-ops-hardening.md`
  - `specs/010-conversation-lifecycle-semantics.md`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Context
Een externe audit heeft 12 bevindingen opgeleverd rond auth, routing, onderhoudbaarheid, schaalbaarheid en teststijl.
Deze spec bepaalt welke punten nu aangepakt worden, welke expliciet gedocumenteerd worden en welke bewust later ingepland worden.

## Doel

1. Een expliciete, verifieerbare scope bepalen voor de eerstvolgende verbetergolf.
2. Contract- en auth-invarianten uit `AGENTS.md` ongewijzigd houden.
3. Niet-essentiële refactors uit de huidige scope houden.

## Contract- En Security Invarianten

1. `POST /events` blijft `audit/v1` contractcompatibel.
2. `conversation_id` blijft een string (geen UUID-verplichting).
3. `messages` blijft niet-leeg en rolvalidatie blijft `user|assistant|summary` voor ingest.
4. Ingest/read key-scheiding blijft strikt (`AUDIT_INGEST_API_KEY` vs `AUDIT_READ_API_KEY`).
5. `AUDIT_API_KEY` blijft buiten gebruik.

## Bevindingen-Triage

| # | Bevinding | Oordeel | Beslissing | Follow-up |
|---|---|---|---|---|
| 1 | In-process login rate limiting schaalt niet over workers/replicas | Correct | Nu aanpakken (ops-hardening + documentatie) | Spec 009 |
| 2 | `require_ingest_auth` wordt manueel aangeroepen | Correct | Nu aanpakken | Spec 007 |
| 3 | `_header_or_request_api_key` bevat redundantie | Correct | Nu aanpakken (vereenvoudigen) | Spec 007 |
| 4 | Grote inline HTML/JS in `routers/ui.py` | Correct als onderhoudsrisico | Later (geen functionele/security regressie nu) | Backlog |
| 5 | `{conversation_id:path}` kan toekomstige routeconflicten geven | Correct als toekomstig risico | Nu expliciet beslissen en testen/documenteren | Spec 008 |
| 6 | Geen paginatie op messages/summaries | Correct | Nu aanpakken | Spec 008 |
| 7 | `asyncio.run()` in sync tests | Correct maar low impact | Later | Backlog |
| 8 | `AUDIT_EVENT_CONTRACT_VERSION` niet gebruikt in runtime | Correct maar low impact | Later | Backlog |
| 9 | `on conflict (id) do nothing` update profile niet | Correct, mogelijk bewust | Nu semantiek expliciet maken | Spec 010 |
| 10 | `ended_at` wordt nooit gezet | Correct | Nu semantiek expliciet maken | Spec 010 |
| 11 | `pytest-asyncio` ontbreekt | Correct maar alleen relevant bij teststijlwissel | Later | Backlog |
| 12 | `Dockerfile` vs `Dockerfile.dev` mogelijk drift | Correct als operationeel risico | Later | Backlog |

## Scope Eerste Implementatiegolf

1. Ingest-auth wiring consistent maken via FastAPI dependency-model.
2. Auth header-resolutie vereenvoudigen zonder auth-gedrag te verzwakken.
3. Bounded reads invoeren voor message/summary detail-endpoints.
4. `conversation_id:path` bewust behouden, met expliciete guardrails voor toekomstige routes.
5. Login rate-limit beperkingen expliciteren voor multi-worker deployments.
6. Conversation lifecycle semantiek (`profile`, `ended_at`) expliciet vastleggen.

## Niet In Scope Voor Deze Golf

1. Migratie van inline UI naar templates/static files.
2. Volledige teststijlmigratie naar `pytest-asyncio`.
3. Runtime gebruik van `AUDIT_EVENT_CONTRACT_VERSION` in response headers.
4. Docker build-pipeline harmonisatie tussen dev en productie images.

## Acceptatiecriteria

1. Voor elk item in de eerste implementatiegolf bestaat een aparte spec met concrete requirements en teststrategie.
2. Uitvoering van de scope veroorzaakt geen contractbreuk op `audit/v1`.
3. Uitvoering van de scope verzwakt geen ingest/read auth checks.

## Rollout

1. Deze triage-spec reviewen en accepteren.
2. Specs 007-010 accepteren.
3. Implementeren in kleine, afzonderlijke wijzigingen met regressietests.
