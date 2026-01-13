import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.db import close_db, init_db
from app.routers import conversations, events
from app.settings import AUDIT_DB_URL, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(app, AUDIT_DB_URL)
    yield
    await close_db(app)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        await conn.execute("select 1")
    return {"status": "ok"}


app.include_router(events.router)
app.include_router(conversations.router)
