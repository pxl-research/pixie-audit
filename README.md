# pixie-audit
Standalone audit API + Postgres stack for logging and querying Pixie chat conversations

## Audit Contract

`POST /events` volgt het gedeelde `audit/v1` contract uit `pixie-contracts`:

- `conversation_id` (string, verplicht)
- `profile` (string, verplicht)
- `messages` (minstens 1 item met `role` in `user|assistant|summary` en `content`)
- `metadata` (optioneel, enkel `location`)

## Conversations Query Filters

`GET /conversations` ondersteunt deze filters:

- `profile` (exacte match)
- `location` (exacte match, case-insensitive, trim toegepast)
- `from` (ISO8601 datetime, inclusieve ondergrens op `started_at`)
- `to` (ISO8601 datetime, inclusieve bovengrens op `started_at`)
- `limit` en `offset` voor paginatie

Voorbeelden:

- `/conversations?location=antwerpen`
- `/conversations?location=Antwerpen&from=2026-02-01T00:00:00Z&to=2026-02-28T23:59:59Z`
