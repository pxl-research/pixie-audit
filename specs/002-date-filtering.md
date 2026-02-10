# Spec 002 - Datumfiltering Voor Audit Logs

## Status
Implemented

## Beslissing

- Gekozen semantiek: strikt datetime (geen datum-only einde-dag vertaling).
- Querygrenzen blijven inclusief (`started_at >= from`, `started_at <= to`).

## Probleem
Datumfiltering is technisch al gedeeltelijk aanwezig in `GET /conversations` via `from` en `to`, maar dit is niet duidelijk verankerd als complete feature in UI, documentatie en testdekking.
Daardoor is het gedrag rond grenzen/tijdzone voor gebruikers en ontwikkelaars niet expliciet genoeg.

## Implementatie

- Geïmplementeerd op: 2026-02-10
- Commits:
  - `2aa2fb6` (`feat(ui): add server-side log filters for location and datetime`)
  - `a66435d` (`test(smoke): verify location and date conversation filters`)

## Implementatiebewijs

- UI datumfilters (`datetime-local` -> ISO8601):
  - `audit-api/app/routers/ui.py`
- API semantiek en documentatie:
  - `audit-api/app/routers/conversations.py`
  - `README.md`
- Testdekking:
  - `audit-api/tests/test_conversations_router.py`
  - `audit-api/tests/smoke/audit_event_contract.py`
- Containerized checks uitgevoerd en groen:
  - compileall, black, ruff, ty, pytest, smoke
  - security baseline: `ruff --select S`, bandit, pip-audit

## Doel

- Datumfiltering expliciet en voorspelbaar maken.
- UI ondersteunen met duidelijke van/tot datuminputs.
- Gedrag rond inclusieve grenzen en timezone standaardiseren.
- Testdekking uitbreiden zodat regressies op datumfilters opvallen.

## Non-Goals

- Geen time-series analytics of aggregaties.
- Geen wijziging aan event ingest contract.
- Geen filteruitbreiding naar complexe relatieve datums (bv. "laatste 7 dagen") in deze fase.

## Huidige Situatie

- `GET /conversations` heeft al:
  - `from` alias -> `from_ts`
  - `to` alias -> `to_ts`
- SQL gebruikt `started_at >= from` en `started_at <= to`.
- UI `/logs` heeft momenteel geen expliciete datumfilters in de interface.

## Functionele Requirements

1. `/logs` UI krijgt invoer voor:
   - `from` (startdatum/tijd)
   - `to` (einddatum/tijd)
2. UI stuurt parameters als ISO8601 naar backend.
3. Backend blijft inclusieve grenzen gebruiken:
   - `started_at >= from`
   - `started_at <= to`
4. Ongeldige datuminput geeft duidelijke `422` validatiefout (FastAPI default + logging).
5. Als enkel `from` of enkel `to` is ingevuld, filtert backend enkel op die grens.

## Niet-Functionele Requirements

1. Gedrag is timezone-consistent:
   - API verwacht/werkt met ISO8601 datums.
   - Opslag en vergelijking op `timestamptz`.
2. Queryperformantie blijft adequaat met bestaande sortering/indexen.

## Technisch Ontwerp

### API

- Endpoint blijft: `GET /conversations`
- Parameters blijven:
  - `from`
  - `to`
- Documenteer expliciet:
  - formaat: ISO8601
  - grenzen inclusief
  - veld waarop gefilterd wordt: `started_at`

### UI

- In `/logs` filters:
  - voeg twee datetime-inputs toe.
  - map naar queryparams `from` en `to`.
  - refresh actie behoudt huidige filters.

### Validatiegedrag

- Geen custom parsing nodig; FastAPI/Pydantic parsing blijft leidend.
- Validation errors blijven via bestaande exception handler.

## Teststrategie

### Unit/API

1. Routertest met enkel `from`.
2. Routertest met enkel `to`.
3. Routertest met beide, controle op SQL-clausules en param-volgorde.
4. Test op limieten/offset gecombineerd met datumfilters.

### UI/Smoke

1. Smoke test scenario dat filtered fetch met `from/to` correct endpoint aanroept.
2. Handmatige smoke: datumveld invullen in `/logs` en resultaatlijst controleren.

### Regressie

1. Bestaande conversation listing zonder datumfilters blijft identiek werken.

## Acceptatiecriteria

1. Datumfilters zijn zichtbaar en bruikbaar in `/logs`.
2. API-gedrag voor `from`/`to` is expliciet gedocumenteerd en getest.
3. Inclusieve grenssemantiek blijft behouden.
4. Containerized baseline checks blijven groen.

## Risico's

- Verwarring rond lokale tijd vs UTC als UI niet duidelijk formatteert.
- Onbedoelde gebruikersverwachting dat `to` op datum zonder tijd “einde dag” betekent.

## Beslissing Log

1. Strikt datetime gekozen.
2. Datum-only UX niet gekozen in deze fase.

## Rollout

1. UI inputs + querystring koppeling.
2. API/documentatie update.
3. Testuitbreiding.
4. Validatie via containerized baseline + smoke.
