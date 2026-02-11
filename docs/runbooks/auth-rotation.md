# Auth Rotation Runbook

Deze runbook beschrijft de minimale veilige rotatie voor auth secrets in `pixie-audit`.

## Scope

- `AUDIT_INGEST_API_KEY`
- `AUDIT_READ_API_KEY`
- `AUDIT_SESSION_SECRET`
- `AUDIT_AUTH_PASSWORD_HASH`

## Voorwaarden

1. Wijzig secrets alleen via je geheime configuratiebron (vault/CI secrets/hosting secrets).
2. Gebruik nooit plaintext wachtwoorden in repo of logs.
3. Plan een kort deployvenster met rollback-optie.

## 1) Ingest key rotatie

1. Genereer nieuwe random key.
2. Update `AUDIT_INGEST_API_KEY` in target environment.
3. Deploy `pixie-audit`.
4. Verifieer:
   - `POST /events` met nieuwe key => `200`
   - `POST /events` met oude key => `401`
5. Update alle producers die events sturen als dat nog niet gebeurd was.

## 2) Read key rotatie

1. Genereer nieuwe random key.
2. Update `AUDIT_READ_API_KEY`.
3. Deploy.
4. Verifieer:
   - `GET /conversations` met nieuwe key => `200`
   - `GET /conversations` met oude key => `401`
5. Update interne read clients/dashboards.

## 3) Session secret rotatie

1. Genereer nieuw random secret.
2. Update `AUDIT_SESSION_SECRET`.
3. Deploy.
4. Verwacht gedrag: bestaande sessiecookies worden ongeldig en users moeten opnieuw inloggen.
5. Verifieer `/login -> /logs` flow met nieuwe sessie.

## 4) Password hash rotatie

1. Maak nieuwe hash (Argon2id):

```bash
docker run --rm python:3.12-slim sh -lc "pip install argon2-cffi && python - <<'PY'
from argon2 import PasswordHasher
print(PasswordHasher().hash('NEW_PASSWORD_HERE'))
PY"
```

2. Update:
   - `AUDIT_AUTH_USER` (optioneel)
   - `AUDIT_AUTH_PASSWORD_HASH` (verplicht)
3. Deploy.
4. Verifieer login met nieuw wachtwoord.
5. Verifieer dat oud wachtwoord `401` geeft.

## Post-rotatie verificatie

1. `GET /health` => `200`
2. Read zonder auth => `401` of redirect naar `/login`
3. Ingest met ingest key => `200`
4. Containerized smoke:
   - `tests.smoke.audit_event_contract`
   - `tests.smoke.auth_login_flow`

## Incident break-glass

Alleen bij incident:

1. Zet tijdelijk `AUDIT_ALLOW_UNAUTHENTICATED_READS=true`.
2. Herstel auth-configuratie.
3. Zet onmiddellijk terug naar `false`.
4. Leg incident en duur van override vast in incidentlog.
