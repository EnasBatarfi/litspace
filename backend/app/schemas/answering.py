# This file defines the Pydantic models for the request and response of the answering API endpoint.

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    chat_id: int | None = None
    selected_paper_ids: list[int] = Field(default_factory=list)
    paper_order_ids: list[int] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=12)
    max_output_tokens: int = Field(default=500, ge=100, le=1200)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query cannot be blank.")
        if not any(char.isalnum() for char in stripped):
            raise ValueError("Query must include words or numbers.")
        return stripped


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


class AnswerTiming(BaseModel):
    retrieval_latency_sec: float | None = None
    generation_latency_sec: float | None = None
    total_latency_sec: float | None = None


class AnswerUsage(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AskResponse(BaseModel):
    project_id: int
    project_slug: str
    chat_id: int | None = None
    query: str
    answer: str
    action: Literal["answer", "clarify", "refuse"] | None = None
    insufficient_evidence: bool
    retrieval_hits_count: int
    used_sources: list[AnswerSource]
    timing: AnswerTiming | None = None
    usage: AnswerUsage | None = None
