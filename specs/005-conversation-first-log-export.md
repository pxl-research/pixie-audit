# Spec 005 - Conversation-First Export Voor Audit Logs

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commits:
  - `c290d6f` (`feat(exports): add auth-protected xlsx logs export endpoint`)
  - `0f8efaf` (`feat(logs-ui): add export-all xlsx action`)

## Implementatiebewijs

- Nieuw export endpoint + mapping/logica:
  - `audit-api/app/routers/exports.py`
  - `audit-api/app/main.py`
- UI exportknop en downloadflow:
  - `audit-api/app/routers/ui.py`
- Testdekking:
  - `audit-api/tests/test_exports_router.py`
  - `audit-api/tests/test_route_auth.py`
  - `audit-api/tests/test_auth_router.py`
- Documentatie:
  - `README.md`
- Containerized checks uitgevoerd:
  - `docker compose up -d --build`
  - health check
  - `compileall`, `black --check`, `ruff check`, `ty check`, `pytest`
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security: `ruff --select S`, `bandit`, `pip-audit`, `gitleaks`, `trivy`

## Beslissingen

- Exportformaat: `.xlsx` (Excel-first, niet-technische gebruikers).
- Exportscope: altijd alle data (geen serverfilters in v1 van export).
- Datamodel: conversation-first, `1` rij per conversatie.
- Samenvatting: gebruik de laatste summary per conversatie (hoogste `created_at`; tie-break op hoogste `id`).
- UI: `/logs` krijgt een knop `Exporteer alles (.xlsx)`.
- Auth: export gebruikt exact dezelfde read-authregels als andere read-endpoints.

## Probleem

De huidige read-flow vereist dat gebruikers conversaties, berichten en samenvattingen zelf aan elkaar koppelen.
Dat is foutgevoelig en tijdsintensief voor niet-technische gebruikers.

## Doel

1. Export leveren die direct bruikbaar is in Excel.
2. Alle context per conversatie in dezelfde rij tonen.
3. Geen manuele koppelstappen tussen datasets nodig maken.
4. Bestaande contracten en auth-invarianten behouden.

## Scope

- Nieuw read-export endpoint voor Excel-download.
- UI-knop in `/logs` om export te starten.
- Conversation-first mapping met samenvatting + volledig gesprek per conversatie.

## Non-Goals

- Geen wijziging aan `POST /events` of `audit/v1` contract.
- Geen vervanging van bestaande read-endpoints (`/conversations`, `/messages`, `/summaries`).
- Geen multi-formaat export in deze fase (`csv/json` buiten scope).
- Geen server-side filtered export in deze fase (eerst "alles exporteren").

## Contract- En Auth-Invarianten

1. `conversation_id` blijft string-based en ongewijzigd.
2. Ingest/read key-scheiding blijft intact (`AUDIT_INGEST_API_KEY` vs `AUDIT_READ_API_KEY`).
3. Export-endpoint is read-only en read-auth beschermd:
   - geldige `X-API-Key: <AUDIT_READ_API_KEY>`, of
   - geldige sessiecookie.
4. `AUDIT_API_KEY` blijft buiten gebruik.

## Functionele Requirements

1. Nieuw endpoint: `GET /exports/logs.xlsx`.
2. Response:
   - `200` met `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
   - `Content-Disposition: attachment; filename="pixie-audit-export-<timestamp>.xlsx"`.
3. Ongeauthenticeerd of foutieve key/session:
   - `401` met bestaande read-authfout.
4. Export bevat alle conversaties op exporttijdstip.
5. Export bevat `1` tabblad: `Conversaties`.
6. Tabblad bevat `1` rij per conversatie met minimaal deze kolommen:
   - `Conversatie ID`
   - `Profiel`
   - `Locatie`
   - `Gestart op`
   - `Beeindigd op`
   - `Aantal berichten`
   - `Samenvatting`
   - `Volledig gesprek`
7. `Samenvatting`:
   - laatste summary voor de conversatie;
   - leeg als er geen summary bestaat.
8. `Volledig gesprek`:
   - alle niet-summary berichten in chronologische volgorde (`created_at asc`);
   - per regel: `[timestamp] <role>: <content>`.
9. `Aantal berichten` telt niet-summary berichten.
10. Rijsortering in export: `Gestart op` aflopend (nieuwste eerst).

## UI Requirements (`/logs`)

1. Voeg knop toe: `Exporteer alles (.xlsx)`.
2. Knop start download van `GET /exports/logs.xlsx`.
3. Tijdens export:
   - knop tijdelijk disabled;
   - zichtbare laadstatus in de UI.
4. Bij fout:
   - duidelijke foutmelding voor gebruiker;
   - geen technische stacktrace in UI.

## Security Requirements

1. Geen secrets of auth-headers loggen.
2. Geen gevoelige payload dumpen in applicatielogs.
3. Spreadsheet formula injection mitigeren voor alle tekstcellen:
   - als celwaarde begint met `=`, `+`, `-` of `@`, prepend met `'`.
4. SQL blijft geparametriseerd.
5. Export-endpoint verzwakt bestaande read-auth niet.

## Technisch Ontwerp (voorgesteld)

### Backend

1. Nieuwe router/module voor exports (additief).
2. Query conversaties (`started_at desc`), plus berichten voor betrokken conversaties.
3. Groepeer berichten per conversatie in backend-code.
4. Selecteer laatste summary deterministisch:
   - sorteer summaries op `(created_at desc, id desc)`, neem eerste.
5. Bouw Excel-bestand server-side en retourneer als downloadresponse.

### Datamapping

1. `Locatie` uit `conversation.metadata.location`, fallback leeg.
2. `Volledig gesprek` bevat alleen rollen `user|assistant|system`.
3. `Samenvatting` komt uit rollen `summary`.
4. Tijdwaarden als leesbare string voor eindgebruikers; formaat consistent binnen bestand.

## Teststrategie

1. Router/auth tests:
   - `401` zonder read-auth;
   - `200` met read key;
   - `200` met geldige sessiecookie.
2. Exportinhoud tests:
   - exact `1` rij per conversatie;
   - laatste summary wordt gekozen bij meerdere summaries;
   - geen summary geeft lege kolom;
   - berichtvolgorde in `Volledig gesprek` is chronologisch.
3. UI tests:
   - exportknop zichtbaar op `/logs`;
   - knop disabled tijdens export;
   - foutmelding bij mislukte export.
4. Regressie:
   - bestaande read-endpoints blijven ongewijzigd functioneren.

## Acceptatiecriteria

1. Een geauthenticeerde gebruiker kan vanuit `/logs` met `1` klik een `.xlsx` downloaden.
2. Export vereist geen manuele koppeling tussen conversaties en samenvattingen.
3. Bij meerdere summaries wordt deterministisch de laatste gebruikt.
4. Read-auth en key-scheiding blijven correct enforced.
5. Bestaande contractinvarianten blijven intact.

## Risico's

1. Grote datasets kunnen exporttijd en geheugengebruik verhogen.
2. Lange gesprekken kunnen zeer grote celwaarden opleveren in `Volledig gesprek`.
3. Onverwachte historische data (zonder metadata/location) kan lege velden tonen.

## Rollout

1. Spec review en expliciete acceptatie.
2. Implementatie in kleine stappen (endpoint, mapping, UI-knop, tests).
3. Containerized validate + relevante security gates volgens `AGENTS.md`.
