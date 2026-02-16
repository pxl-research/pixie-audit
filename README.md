# pixie-audit
Standalone audit API + Postgres stack for logging and querying Pixie chat conversations

## Audit Contract

`POST /events` volgt het gedeelde `audit/v1` contract uit `pixie-contracts`:

- `conversation_id` (string, verplicht)
- `profile` (string, verplicht)
- `messages` (minstens 1 item met `role` in `user|assistant|summary` en `content`)
- `metadata` (optioneel, enkel `location`)

## Authentication Model

Ingest en read access zijn gescheiden:

- `POST /events` vereist `X-API-Key: <AUDIT_INGEST_API_KEY>`
- read endpoints vereisen:
  - geldige sessie-cookie (`audit_session`), of
  - `X-API-Key: <AUDIT_READ_API_KEY>`

Read endpoints:

- `GET /logs`
- `GET /conversations`
- `GET /conversations/{conversation_id}/messages`
- `GET /conversations/{conversation_id}/summaries`
- `GET /exports/logs.xlsx`

Browser flow:

- `GET /login` toont loginpagina.
- `POST /auth/login` zet sessie-cookie en redirectt naar `/logs`.
- `POST /auth/logout` wist sessie-cookie.
- `GET /auth/me` geeft huidige ingelogde user terug.

## Conversations Query Filters

`GET /conversations` ondersteunt deze filters:

- `profile` (exacte match)
- `location` (exacte match, case-insensitive, trim toegepast; herhaalbaar voor OR-filtering)
- `from` (ISO8601 datetime, inclusieve ondergrens op `started_at`)
- `to` (ISO8601 datetime, inclusieve bovengrens op `started_at`)
- `limit` en `offset` voor paginatie

Voorbeelden:

- `/conversations?location=antwerpen`
- `/conversations?location=antwerpen&location=gent`
- `/conversations?location=Antwerpen&from=2026-02-01T00:00:00Z&to=2026-02-28T23:59:59Z`

`GET /conversations/{conversation_id}/messages` en
`GET /conversations/{conversation_id}/summaries` ondersteunen:

- `limit` (default `200`, server-side begrensd tot `1..1000`)
- `offset` (default `0`, server-side begrensd tot minimum `0`)

`conversation_id` blijft string-based; IDs met `/` blijven toegestaan mits URL-encoding.

Voor `/logs` kan je vooraf gedefinieerde filterlocaties tonen via:

- `AUDIT_ALLOWED_LOCATIONS=antwerpen, gent` (of pipe-separated `antwerpen|gent`)
- fallback: `ACTIVE_CLIENT_ALLOWED_LOCATIONS` (zelfde formaat)
