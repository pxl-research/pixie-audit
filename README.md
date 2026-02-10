# pixie-audit
Standalone audit API + Postgres stack for logging and querying Pixie chat conversations

## Audit Contract

`POST /events` volgt het gedeelde `audit/v1` contract uit `pixie-contracts`:

- `conversation_id` (string, verplicht)
- `profile` (string, verplicht)
- `messages` (minstens 1 item met `role` in `user|assistant|summary` en `content`)
- `metadata` (optioneel, enkel `location`)
