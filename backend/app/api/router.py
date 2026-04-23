# This file defines the main API router for the application, which includes all the individual route modules.

from fastapi import APIRouter

from app.api.routes import answering, chats, chunking, health, indexing, parsing, projects, query, upload

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router)
api_router.include_router(chats.router)
api_router.include_router(upload.router)
api_router.include_router(parsing.router)
api_router.include_router(chunking.router)
api_router.include_router(indexing.router)
api_router.include_router(query.router)
api_router.include_router(answering.router)
