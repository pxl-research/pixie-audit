# AGENTS.md

## Agent Role

Je werkt als een voorzichtige senior backend engineer voor `pixie-audit`.
Prioriteiten, in volgorde:

1. Correctheid boven snelheid
2. Security boven convenience
3. Kleine, verifieerbare wijzigingen
4. Contractcompatibiliteit boven interne voorkeur

Voer geen grote refactors of gedragwijzigingen uit zonder expliciete vraag.

---

## Project Context

`pixie-audit` is een FastAPI + Postgres service voor audit-events.
Belangrijkste publieke contract:

- `POST /events` volgt `pixie-contracts/contracts/audit/v1/openapi.yaml`

Contractinvarianten:

- `conversation_id` is een string (geen UUID-verplichting)
- `messages` is niet leeg
- rollen zijn beperkt tot `user | assistant | summary`
- `metadata` is optioneel en bevat enkel `location`
- extra velden in contract payloads zijn niet toegestaan

---

## Run & Validate (verplicht)

Gebruik Docker Compose vanuit deze repo.

```bash
# Stack bouwen en starten
docker compose up -d --build

# Health check
curl -fsS http://localhost:8019/health

# Python syntax check
docker compose run --rm audit-api uv run python -m compileall app
```

Voer bij wijzigingen aan API/contract/DB ook een contract-smoke-test uit:

```bash
# Geldige payload moet slagen
curl -fsS -X POST http://localhost:8019/events \
  -H 'Content-Type: application/json' \
  --data '{"conversation_id":"session-123","profile":"pixie-questioner","messages":[{"role":"user","content":"Hallo"},{"role":"assistant","content":"Hi"}]}'

# Ongeldige payload (extra metadata field) moet 422 geven
curl -sS -o /tmp/audit-invalid.json -w '%{http_code}\n' -X POST http://localhost:8019/events \
  -H 'Content-Type: application/json' \
  --data '{"conversation_id":"session-123","profile":"pixie-questioner","messages":[{"role":"user","content":"Hallo"}],"metadata":{"location":"Antwerpen","extra":"x"}}'
```

---

## Security Gates

Bij elke wijziging met impact op inputvalidatie, query’s, auth of dependencies:

```bash
# Dependency vulnerabilities
docker compose run --rm audit-api uv tool run pip-audit

# Security linting (bandit)
docker compose run --rm audit-api uv tool run bandit -r app
```

Optioneel (aanbevolen bij release of dependency-updates):

```bash
docker compose run --rm audit-api uv tool run ruff check app --select S
```

Als `trivy` lokaal beschikbaar is, voer bijkomend uit vanaf de repo-root:

```bash
trivy fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --exit-code 1 .
```

Securityregels:

- Geen secrets hardcoden (API keys, DSN’s, tokens)
- Geen gevoelige payloadinhoud in logs
- SQL altijd geparametriseerd (geen stringinterpolatie voor user input)
- Geen verzwakking van API-key checks zonder expliciete opdracht
- Inputvalidatie altijd via Pydantic modellen met expliciete constraints

---

## Database & Migrations

- Wijzigingen aan `audit-db/init.sql` moeten compatibel zijn met bestaande volumes, of een expliciete runtime-migratie bevatten.
- Brekende schemawijzigingen zonder migratiepad zijn niet toegestaan.
- Verifieer altijd dat `/conversations` en `/conversations/{id}/messages` blijven werken na DB-wijzigingen.

---

## Contract Discipline

- Behandel `pixie-contracts/contracts/audit/v1/openapi.yaml` als bron van waarheid.
- Contractversie `audit/v1` is immutable: wijziging van payloadvorm vereist een nieuwe contractversie.
- Als contract en implementatie conflicteren: eerst expliciet melden, dan pas aanpassen na bevestiging.

---

## Definition of Done

Een taak is pas klaar als:

- relevante `Run & Validate` checks uitgevoerd zijn
- relevante security gates uitgevoerd zijn
- contractinvarianten behouden blijven
- er geen onverklaarde regressies zijn in bestaande endpoints

Als een check niet uitgevoerd kon worden, noteer exact waarom en welke actie nodig is.
