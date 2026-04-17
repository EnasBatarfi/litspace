# This file defines the Pydantic models for the retrieval API endpoints.

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=8, ge=1, le=20)


class RetrievalHit(BaseModel):
    chunk_id: str
    paper_id: int
    project_id: int
    project_slug: str
    chunk_index: int
    page_start: int
    page_end: int
    section_heading: str | None = None
    paper_title: str | None = None
    original_filename: str | None = None
    text: str
    semantic_rank: int | None = None
    lexical_rank: int | None = None
    hybrid_score: float


class RetrievalResponse(BaseModel):
    project_id: int
    project_slug: str
    query: str
    top_k: int
    total_hits: int
    hits: list[RetrievalHit]