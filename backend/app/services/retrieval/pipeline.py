# This module defines the retrieval pipeline that combines both semantic and lexical retrieval methods to provide a more comprehensive set of results for a given query. The `hybrid_retrieve` function orchestrates the retrieval process by first obtaining results from both the semantic and lexical retrievers, and then merging these results using a reciprocal rank fusion technique to produce a final ranked list of hits.

from __future__ import annotations

from app.services.retrieval.bm25_retriever import lexical_retrieve
from app.services.retrieval.chroma_retriever import semantic_retrieve
from app.services.retrieval.hybrid import reciprocal_rank_fusion


def hybrid_retrieve(
    project_slug: str,
    query: str,
    top_k: int,
    paper_ids: list[int] | None = None,
) -> list[dict]:
    semantic_hits = semantic_retrieve(
        project_slug=project_slug,
        query=query,
        top_k=max(top_k, 10),
        paper_ids=paper_ids,
    )
    lexical_hits = lexical_retrieve(
        project_slug=project_slug,
        query=query,
        top_k=max(top_k, 10),
        paper_ids=paper_ids,
    )
    merged_hits = reciprocal_rank_fusion(
        semantic_hits=semantic_hits,
        lexical_hits=lexical_hits,
        top_k=top_k,
    )
    return merged_hits
