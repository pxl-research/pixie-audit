# Spec 009 - Login Rate Limit Schaalbaarheid En Operationele Hardening

## Status
Implemented

## Implementatie

- Geïmplementeerd op: 2026-02-16
- Commit:
  - `docs(auth): document rate-limit scope and scaled deployment requirements (spec-009)`

## Implementatiebewijs

- Auth-model documentatie met limiter-scope:
  - `README.md`
- Operationeel runbook met edge/proxy hardeningrichtlijnen:
  - `docs/runbooks/auth-rotation.md`
- Containerized checks uitgevoerd en groen:
  - health, compileall, black, ruff, ty, pytest
  - smoke: `audit_event_contract`, `auth_login_flow`
  - security baseline: `ruff --select S`, bandit, pip-audit

## Probleem
De huidige login rate limiter gebruikt in-memory processtate.
Bij meerdere app-workers of meerdere container replicas wordt die state niet gedeeld, waardoor effectieve bescherming per process geldt in plaats van servicebreed.

## Doel

1. Securitygedrag correct documenteren voor productie-operatoren.
2. Foutieve assumptie vermijden dat app-level limiter alleen voldoende is in horizontaal geschaalde setup.
3. Minimale, veilige hardening toevoegen zonder grote architectuurwijziging.

## Scope

- `audit-api/app/auth.py` (optionele startup/warning hook)
- `README.md`
- `docs/runbooks/auth-rotation.md` of aparte operations-sectie
- eventueel `specs/003-read-auth-hardening.md` verwijzing/appendix

## Non-Goals

1. Geen Redis- of DB-backed distributed limiter in deze fase.
2. Geen wijziging aan login UX of sessiemodel.
3. Geen wijziging aan ingest/read key-model.

## Beslissingen (voorgesteld)

1. In-process limiter blijft bestaan als baseline (single-process bescherming).
2. Productievereiste wordt expliciet:
   - aanvullende rate limiting op reverse proxy/ingress niveau.
3. Documentatie moet ondubbelzinnig aangeven dat limiter niet worker- of replica-overstijgend is.
4. Optioneel: startup-warning wanneer configuratie wijst op multi-worker risico.

## Functionele Requirements

1. Operationele documentatie vermeldt expliciet:
   - limiter key = `ip+username`;
   - limiter scope = per Python process;
   - multi-worker/replica effect.
2. Security runbook bevat concrete deploymentrichtlijn voor edge/proxy rate limits op `/auth/login`.
3. Indien startup-warning geïmplementeerd wordt:
   - warning zonder secrets;
   - geen startup-fail (informatief, niet blocker).

## Security Requirements

1. Geen schijnveiligheid in docs of defaults.
2. Geen verzwakking van bestaande `429` gedrag binnen één process.
3. Auth failure logging blijft secretvrij.

## Technisch Ontwerp (voorgesteld)

1. Documentatie-uitbreiding in README onder auth-model.
2. Runbook-uitbreiding met proxyvoorbeeld (Nginx/Traefik conceptueel; geen hardcoded infra-aanname).
3. Eventuele startup-warning gebaseerd op detecteerbare workerconfig (best-effort).

## Teststrategie

1. Regressietests voor bestaande limitergedrag blijven groen (`401/429` flow).
2. Indien warning toegevoegd: unit-test op warning-conditie (zonder env secrets).
3. Geen load/performance test in deze fase.

## Acceptatiecriteria

1. Repo-documentatie maakt limiter-scope expliciet en ondubbelzinnig.
2. Operationele guidance benoemt verplichte aanvullende edge-rate-limit.
3. Bestaande login rate-limit tests blijven groen.

## Risico's

1. Zonder aanvullende infra-rate-limit blijft brute-force exposure bestaan in geschaalde deployment.
2. Worker-detectie voor warning kan omgeving-specifiek onvolledig zijn.

## Rollout

1. Docs/runbook hardenen.
2. Optionele startup-warning toevoegen.
3. Regressietests draaien.
4. Security gates voor auth-gerelateerde wijziging uitvoeren.
