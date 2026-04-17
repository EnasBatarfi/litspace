# This file defines the Pydantic models for the indexing process, which are used to structure the data related to project indexing and its response.

from pydantic import BaseModel


class ProjectIndexResponse(BaseModel):
    project_id: int
    project_slug: str
    total_project_papers: int
    total_indexed_papers: int
    indexed_paper_ids: list[int]
    total_chunks_indexed: int
    embedding_model: str
    chroma_collection: str
    bm25_index_path: str