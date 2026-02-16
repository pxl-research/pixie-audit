# Spec 010 - Conversation Lifecycle Semantiek (Profile En EndedAt)

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commit:
  - `docs(events): codify conversation lifecycle semantics for profile and ended_at (spec-010)`

## Implementatiebewijs

- Lifecycle-semantiek gedocumenteerd:
  - `README.md`
- Regressie-asserties rond conflictgedrag en `ended_at`:
  - `audit-api/tests/test_events_router.py`
  - `audit-api/tests/test_conversations_router.py`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Probleem
Twee huidige gedragingen zijn niet expliciet vastgelegd:

1. `insert ... on conflict (id) do nothing` op `audit.conversations` maakt `profile` en metadata effectief first-write-wins.
2. `ended_at` bestaat in schema/output maar wordt nooit geschreven en blijft dus meestal `NULL`.

Zonder expliciete semantiek is onduidelijk of dit bewust gedrag is of technische schuld.

## Doel

1. Verwachte lifecycle-semantiek expliciet vastleggen.
2. Onbedoelde gedragwijzigingen vermijden in toekomstige fixes.
3. Contractcompatibiliteit behouden zolang `audit/v1` geen expliciet eindevent definieert.

## Scope

- `audit-api/app/routers/events.py`
- `audit-db/init.sql` (alleen indien semantiekwijziging schema vereist)
- `README.md`
- router/smoke tests waar lifecycle-gedrag geraakt wordt

## Non-Goals

1. Geen nieuwe contractversie in deze fase.
2. Geen heuristische/afgeleide `ended_at` op basis van laatste message zonder expliciete productbeslissing.
3. Geen retroactieve datamigratie van historische conversaties in deze fase.

## Beslissingen (voorgesteld)

1. **Profile semantiek**: voorlopig first-write-wins behouden.
2. **EndedAt semantiek**: voorlopig `NULL` tenzij er een expliciet afsluitsignaal bestaat in contract (momenteel niet aanwezig).
3. Beide beslissingen expliciet documenteren als `audit/v1` gedrag.
4. Eventuele wijziging naar profile-updates of ended-at berekening vereist nieuwe, expliciete spec met migratie-impactanalyse.

## Functionele Requirements

1. Gedrag rond `on conflict (id) do nothing` wordt gedocumenteerd in README/spec.
2. Gedrag rond `ended_at` wordt gedocumenteerd als "momenteel niet ingevuld door ingest-flow".
3. Bestaande endpointresponses blijven contractcompatibel.

## Teststrategie

1. Regressietest dat herhaalde events met zelfde `conversation_id` geen onbedoelde profile-overschrijving forceren.
2. Regressietest dat `ended_at` in huidige ingest-flow `NULL` kan blijven zonder fout.
3. Bestaande smoke-tests voor `/conversations` en `/conversations/{id}/messages` blijven groen.

## Acceptatiecriteria

1. Lifecycle-semantiek is expliciet beschreven en testbaar.
2. Geen impliciete gedragwijziging zonder aparte beslissing.
3. Geen regressie op bestaande read-endpoints.

## Risico's

1. Sommige stakeholders kunnen profile-update verwachten bij latere events met afwijkend profile.
2. `ended_at = NULL` kan verwarring geven in rapportering zonder extra toelichting.

## Rollout

1. Beslissingen bevestigen.
2. Documentatie + regressietests aligneren met gekozen semantiek.
3. Eventuele toekomstige wijziging pas via nieuwe spec/contractafweging.
