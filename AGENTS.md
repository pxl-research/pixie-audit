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
- read endpoints (`/logs`, `/conversations`, `/messages`, `/summaries`) zijn auth-protected

Contractinvarianten:

- `conversation_id` is een string (geen UUID-verplichting)
- `messages` is niet leeg
- rollen zijn beperkt tot `user | assistant | summary`
- `metadata` is optioneel en bevat enkel `location`
- extra velden in contract payloads zijn niet toegestaan

Auth-invarianten:

- ingest gebruikt `AUDIT_INGEST_API_KEY`
- read API gebruikt `AUDIT_READ_API_KEY` of geldige sessiecookie
- `AUDIT_API_KEY` wordt niet meer gebruikt

---

## Run & Validate (verplicht)

Alles wordt in containers uitgevoerd.
Gebruik geen host-level `uv`, `pytest`, `python`, `curl` of security tools.
Gebruik Docker Compose (en voor Trivy een aparte Docker container).
Als uitzondering niet expliciet in dit document staat, is host-uitvoering verboden.
Commando's voor checks moeten starten met `docker compose ...` of `docker run ...`.

```bash
# Stack bouwen en starten
docker compose up -d --build

# Health check (vanuit container naar service)
docker compose exec -T audit-api uv run python -c "import urllib.request, json; print(json.loads(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode()))"

# Python syntax check
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv run python -m compileall app tests"

# Formatting check
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run black --check app tests"

# Lint
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run ruff check app tests"

# Type check
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run ty check"

# Test suite
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv run pytest"
```

Voer bij wijzigingen aan API/contract/DB ook een contract-smoke-test uit:

```bash
# Implementatie: audit-api/tests/smoke/audit_event_contract.py
docker compose exec -T audit-api uv run python -m tests.smoke.audit_event_contract
```

Voer bij wijzigingen aan auth flow ook de auth-smoke-test uit:

```bash
# Implementatie: audit-api/tests/smoke/auth_login_flow.py
docker compose exec -T audit-api uv run python -m tests.smoke.auth_login_flow
```

---

## Testing Policy

- Elke wijziging aan `app/schemas.py`, `app/adapters/*`, `app/routers/*` of DB-querylogica vereist bijhorende testupdates.
- Bugfixes moeten een regressietest bevatten die het gewenste gedrag afdekt.
- Security-gedrag rond auth en inputvalidatie moet expliciet getest blijven.
- Nieuwe tests horen onder `audit-api/tests/`.

Minimaal te behouden testfocus:

- Contractvorm en validatie (`audit/v1`)
- Adaptermapping contract -> intern model
- Routergedrag voor persist/query flows
- ingest/read key-scheiding (`401` bij foutieve of verkeerde sleutel)
- session-auth gedrag voor `/logs` en read-endpoints

---

## Security Gates

Bij elke wijziging met impact op inputvalidatie, query’s, auth of dependencies:

```bash
# Security linting rules (ruff S)
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run ruff check app --select S"

# SAST scan (bandit)
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run bandit -r app"

# Dependency vulnerabilities
docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv tool run pip-audit"
```

`ruff --select S` draait op `app` (productiecode). Testcode blijft gedekt door gewone lint + tests.

Aanbevolen extra bij release of dependency-updates:

```bash
docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:latest detect \
  --source /repo \
  --redact \
  --no-banner \
  --exit-code 1
```

Trivy-scan altijd in container uitvoeren:

```bash
docker run --rm -v "$PWD:/work" -w /work aquasec/trivy:latest fs \
  --scanners vuln,misconfig,secret \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  .
```

Securityregels:

- Geen secrets hardcoden (API keys, DSN’s, tokens)
- Geen gevoelige payloadinhoud in logs
- SQL altijd geparametriseerd (geen stringinterpolatie voor user input)
- Geen verzwakking van ingest/read auth checks zonder expliciete opdracht
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
- `black --check`, `ruff check` en `ty check` groen zijn
- `docker compose run --rm audit-api sh -lc "uv sync --frozen --group dev && uv run pytest"` groen is
- relevante security gates uitgevoerd zijn
- contractinvarianten behouden blijven
- er geen onverklaarde regressies zijn in bestaande endpoints

Als een check niet uitgevoerd kon worden, noteer exact waarom en welke actie nodig is.
