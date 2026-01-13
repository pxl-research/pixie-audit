import asyncpg
from fastapi import FastAPI


async def init_db(app: FastAPI, dsn: str) -> None:
    if not dsn:
        raise RuntimeError("AUDIT_DB_URL is required")
    app.state.db = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)


async def close_db(app: FastAPI) -> None:
    pool = getattr(app.state, "db", None)
    if pool is not None:
        await pool.close()
