import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import validate_auth_configuration
from app.db import close_db, init_db
from app.routers import auth, conversations, events, ui
from app.settings import AUDIT_DB_URL, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_configuration()
    await init_db(app, AUDIT_DB_URL)
    yield
    await close_db(app)


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
async def health(request: Request):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        await conn.execute("select 1")
    return {"status": "ok"}


app.include_router(events.router)
app.include_router(conversations.router)
app.include_router(ui.router)
app.include_router(auth.router)
