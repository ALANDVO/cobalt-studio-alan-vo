"""Cobalt Studio API. Local runs and Docker both use ``app.main:app``."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.db import default_database_path, init_db
from app.core.version import product_version

_LOCAL_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]


def create_app(database_path: str | None = None) -> FastAPI:
    path = database_path or default_database_path()
    init_db(path)
    app = FastAPI(title="Cobalt Studio", version=product_version())
    app.state.database_path = path
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_LOCAL_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)
    return app


app = create_app()
