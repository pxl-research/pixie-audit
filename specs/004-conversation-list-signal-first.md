# Spec 004 - Conversation List Signal-First UX

## Status
Implemented

## Beslissing Log

- Beslist op: 2026-02-11
- Scope: enkel Spec 004 delivery
- Groeperingstijdsbasis: browser lokale tijd
- `conversation_id` zichtbaarheid: alleen detailpaneel

## Implementatie

- Geïmplementeerd op: 2026-02-11
- Commits:
  - `6fe7c74` (`docs(spec-004): accept scope and decisions`)
  - `107b112` (`feat(logs-ui): group conversations by recency and location`)
  - `f23ddfe` (`test(logs-ui): cover grouped signal-first list template`)

## Implementatiebewijs

- UI lijstweergave en recency-groepering:
  - `audit-api/app/routers/ui.py`
- Template regressietests:
  - `audit-api/tests/test_auth_router.py`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Probleem
De huidige lijstweergave in `/logs` toont per item:

- titel: `profile` (meestal altijd dezelfde winkel in deze setup)
- metadata: datum/tijd
- metadata: `conversation_id`

Voor operators geeft dit weinig signaal:

- `profile` voegt nauwelijks onderscheid toe bij single-store gebruik;
- `conversation_id` is intern technisch en niet betekenisvol voor triage;
- de relevante context voor snelle interpretatie is vooral `location` + tijd.

## Doel

1. De lijst sneller scanbaar maken voor operationeel gebruik.
2. Relevante informatie visueel prioriteren (`location`, tijd).
3. Ruis verminderen (niet-significante velden uit de lijst verwijderen).
4. Gesprekken intuïtief groepeerbaar maken op recency.

## Scope

- Alleen `/logs` lijstweergave (HTML/JS in `audit-api/app/routers/ui.py`).
- Geen wijziging aan ingest-contract of DB-schema.
- Geen breaking change aan bestaande read endpoints.

## Non-Goals

- Geen wijziging aan `POST /events` of `audit/v1`.
- Geen server-side extra endpoint voor groepering.
- Geen analytics/aggregatie buiten eenvoudige tijdsindeling.

## Beslissing (voorgesteld)

### 1. Lijstitem-inhoud

- **Titel**: `location`
  - bron: `conversation.metadata.location`
  - fallback: `"Onbekende locatie"`
- **Subtitel**: lokale datum/tijd van `started_at`
  - formaat via bestaande JS formatter (`nl-BE`)
- **Niet tonen in lijst**:
  - `profile`
  - `conversation_id`

### 2. Recency-groepering in de lijst

Gesprekken worden client-side gegroepeerd in vaste secties:

1. `Vandaag`
2. `Gisteren`
3. `Afgelopen 7 dagen`
4. `Ouder`

Regels op basis van lokaal kalenderdagverschil t.o.v. `now`:

- `0 dagen`: Vandaag
- `1 dag`: Gisteren
- `2..7 dagen`: Afgelopen 7 dagen
- `>= 8 dagen`: Ouder

Binnen elke sectie:

- sortering `started_at desc` (nieuwste eerst)

Secties zonder items:

- niet renderen

## Alternatieven (afgewogen)

1. Alleen `location` als titel, zonder groepering.
   - Pro: minimale wijziging.
   - Con: minder scanbaar bij grotere lijsten.
2. Alleen groepering houden, maar huidige titel (`profile`) behouden.
   - Pro: kleine visuele impact.
   - Con: belangrijkste signaal (`location`) blijft onderbenut.

Voorkeur: combineer beide (signal-first + recency-groepen).

## Technisch Ontwerp

### UI data mapping

Per conversation-item in lijst:

- `title = normalizedLocation || "Onbekende locatie"`
- `subtitle = formatTime(started_at)`

Waar `normalizedLocation`:

- `trim()` op string
- leeg -> `null`

### Groeperingsfunctie (client-side)

Nieuwe helper in inline script:

- parse `started_at` naar `Date`
- bereken dagverschil t.o.v. lokale middernacht
- map naar bucket key

Aanbevolen interne bucketvolgorde:

1. `today`
2. `yesterday`
3. `last_7_days`
4. `older`

### Detailpaneel

- Mag `conversation_id` nog tonen in detailheader voor debugging/audit traceability.
- Lijstweergave blijft bewust vrij van technische identifiers.

## Teststrategie

### Unit/Router tests

- Geen API-contractwijziging verwacht.
- Bestaande routertests blijven leidend (geen regressie in `/conversations` payload).

### UI gedrag (smoke/handmatig)

1. Item met `metadata.location` toont location als titel.
2. Item zonder location toont `"Onbekende locatie"`.
3. `conversation_id` verschijnt niet in de lijst.
4. Groepen worden in juiste volgorde gerenderd.
5. Gesprekken vallen correct in `Vandaag/Gisteren/Afgelopen 7 dagen/Ouder`.
6. Binnen elke groep staan nieuwste gesprekken bovenaan.

### Regressie

1. Selectie van een conversation blijft messages laden.
2. Bestaande serverfilters (`location`, `from`, `to`) blijven werken.
3. Auth-flow voor `/logs` blijft ongewijzigd.

## Acceptatiecriteria

1. Lijst toont geen `profile` en geen `conversation_id`.
2. Lijsttitel is `location` met fallback `"Onbekende locatie"`.
3. Lijst is gegroepeerd in recency-secties met correcte toewijzing.
4. Er zijn geen regressies op bestaande filter- en selecteerflows.
5. AGENTS-validatie en security-baseline blijven groen in Docker.

## Risico's

1. Tijdzoneverwarring rond daggrenzen (client local time vs UTC opslag).
2. Historische data zonder `metadata.location` leidt tot veel fallbacklabels.

Mitigatie:

- expliciete lokale daggrensregels in implementatie;
- duidelijke fallbacklabel.

## Rollout

1. UI rendering aanpassen (lijstitem + groepering).
2. Handmatige smoke/QA op grensgevallen (middernacht, ontbrekende location).
3. Containerized checks volgens `AGENTS.md`.
