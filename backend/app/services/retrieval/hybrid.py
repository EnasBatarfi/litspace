# This file to retrieve relevant chunks using hybrid lexical and semantic matching.

from __future__ import annotations


def reciprocal_rank_fusion(
    semantic_hits: list[dict],
    lexical_hits: list[dict],
    top_k: int = 8,
    k: int = 60,
) -> list[dict]:
    merged: dict[str, dict] = {}

    for hit in semantic_hits:
        chunk_id = hit["chunk_id"]
        if chunk_id not in merged:
            merged[chunk_id] = {**hit}
        else:
            merged[chunk_id].update(hit)

        rank = hit["semantic_rank"]
        merged[chunk_id]["semantic_rank"] = rank
        merged[chunk_id]["hybrid_score"] = merged[chunk_id].get("hybrid_score", 0.0) + 1.0 / (k + rank)

    for hit in lexical_hits:
        chunk_id = hit["chunk_id"]
        if chunk_id not in merged:
            merged[chunk_id] = {**hit}
        else:
            merged[chunk_id].update(hit)

        rank = hit["lexical_rank"]
        merged[chunk_id]["lexical_rank"] = rank
        merged[chunk_id]["hybrid_score"] = merged[chunk_id].get("hybrid_score", 0.0) + 1.0 / (k + rank)

    ranked = sorted(
        merged.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True,
    )

    return ranked[:top_k]