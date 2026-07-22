from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.config import Settings
from app.db import Database


def create_app(
    *, settings: Settings | None = None, create_schema: bool = True
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    database = Database(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if create_schema:
            database.create_schema()
        yield
        database.dispose()

    application = FastAPI(
        title="CloudSec Copilot API",
        version="0.1.0",
        description="Auditable ingestion and analysis of AWS CloudTrail-style events.",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = database
    application.include_router(router)
    return application


app = create_app()

