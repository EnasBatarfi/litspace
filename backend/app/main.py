# This is the main entry point for the FastAPI application. It sets up the application, including database initialization and middleware configuration.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401
from app.api.router import api_router
from app.db.base import Base
from app.db.session import engine
from app.utils.paths import ensure_base_data_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_base_data_directories()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LitSpace API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
