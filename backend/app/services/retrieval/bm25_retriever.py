# This file to retrieve relevant chunks using BM25 lexical matching. 

from __future__ import annotations

import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.services.indexing.bm25_indexer import tokenize_for_bm25
from app.utils.paths import get_project_bm25_path


def lexical_retrieve(
    project_slug: str,
    query: str,
    top_k: int = 10,
) -> list[dict]:
    bm25_path = get_project_bm25_path(project_slug)
    payload = json.loads(Path(bm25_path).read_text(encoding="utf-8"))

    entries = payload["entries"]
    tokenized_corpus = [entry["tokens"] for entry in entries]

    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = tokenize_for_bm25(query)
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(
        zip(entries, scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    hits: list[dict] = []
    for idx, (entry, score) in enumerate(ranked):
        hits.append(
            {
                "chunk_id": entry["chunk_id"],
                "paper_id": int(entry["paper_id"]),
                "project_id": int(entry["project_id"]),
                "project_slug": entry["project_slug"],
                "chunk_index": int(entry["chunk_index"]),
                "page_start": int(entry["page_start"]),
                "page_end": int(entry["page_end"]),
                "section_heading": entry.get("section_heading") or None,
                "paper_title": entry.get("paper_title") or None,
                "original_filename": entry.get("original_filename") or None,
                "text": entry["text"],
                "bm25_score": float(score),
                "lexical_rank": idx + 1,
            }
        )

    return hits