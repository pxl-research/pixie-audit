import json
import logging

import asyncpg
from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


async def _column_data_type(
    conn: asyncpg.Connection, table_name: str, column_name: str
) -> str | None:
    return await conn.fetchval(
        "select data_type from information_schema.columns "
        "where table_schema = 'audit' and table_name = $1 and column_name = $2",
        table_name,
        column_name,
    )


async def _conversation_fk_name(conn: asyncpg.Connection) -> str | None:
    return await conn.fetchval("""
        select tc.constraint_name
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        where tc.table_schema = 'audit'
          and tc.table_name = 'messages'
          and tc.constraint_type = 'FOREIGN KEY'
          and kcu.column_name = 'conversation_id'
        limit 1
        """)


async def _migrate_conversation_id_columns(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            conversation_id_type = await _column_data_type(conn, "conversations", "id")
            message_conversation_id_type = await _column_data_type(
                conn, "messages", "conversation_id"
            )

            needs_conversation_migration = conversation_id_type == "uuid"
            needs_message_migration = message_conversation_id_type == "uuid"
            if not (needs_conversation_migration or needs_message_migration):
                return

            logger.info(
                "Migrating audit conversation_id columns to text "
                "(conversations.id=%s, messages.conversation_id=%s)",
                conversation_id_type,
                message_conversation_id_type,
            )

            fk_name = await _conversation_fk_name(conn)
            if fk_name:
                await conn.execute(
                    f"alter table audit.messages drop constraint {_quote_ident(fk_name)}"
                )

            if needs_message_migration:
                await conn.execute(
                    "alter table audit.messages "
                    "alter column conversation_id type text using conversation_id::text"
                )

            if needs_conversation_migration:
                await conn.execute(
                    "alter table audit.conversations "
                    "alter column id type text using id::text"
                )

            fk_name = await _conversation_fk_name(conn)
            if fk_name is None:
                await conn.execute(
                    "alter table audit.messages "
                    "add constraint messages_conversation_id_fkey "
                    "foreign key (conversation_id) references audit.conversations(id)"
                )


async def _ensure_location_filter_index(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "create index if not exists audit_conversations_location_norm_idx "
            "on audit.conversations ((lower(trim(metadata->>'location'))))"
        )


async def init_db(app: FastAPI, dsn: str) -> None:
    if not dsn:
        raise RuntimeError("AUDIT_DB_URL is required")
    pool = await asyncpg.create_pool(
        dsn=dsn, min_size=1, max_size=5, init=_init_connection
    )
    await _migrate_conversation_id_columns(pool)
    await _ensure_location_filter_index(pool)
    app.state.db = pool


async def close_db(app: FastAPI) -> None:
    pool = getattr(app.state, "db", None)
    if pool is not None:
        await pool.close()
