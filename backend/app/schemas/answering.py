# This file defines the Pydantic models for the request and response of the answering API endpoint.

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=6, ge=1, le=12)
    max_output_tokens: int = Field(default=500, ge=100, le=1200)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)


class AnswerSource(BaseModel):
    source_id: str
    chunk_id: str
    paper_id: int
    section_heading: str | None = None
    paper_title: str | None = None
    original_filename: str | None = None
    page_start: int
    page_end: int
    hybrid_score: float
    excerpt: str


class AskResponse(BaseModel):
    project_id: int
    project_slug: str
    query: str
    answer: str
    insufficient_evidence: bool
    retrieval_hits_count: int
    used_sources: list[AnswerSource]