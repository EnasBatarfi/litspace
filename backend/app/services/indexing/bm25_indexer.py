# This module provides functionality to build and save a BM25 index payload for a given set of records.

from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


def tokenize_for_bm25(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def build_bm25_payload(
    project_id: int,
    project_slug: str,
    records: list[dict],
) -> dict:
    entries: list[dict] = []
    tokenized_corpus: list[list[str]] = []

    for record in records:
        tokens = tokenize_for_bm25(record["text"])
        tokenized_corpus.append(tokens)

        entries.append(
            {
                "chunk_id": record["chunk_id"],
                "paper_id": record["paper_id"],
                "project_id": record["project_id"],
                "project_slug": record["project_slug"],
                "chunk_index": record["chunk_index"],
                "page_start": record["page_start"],
                "page_end": record["page_end"],
                "section_heading": record.get("section_heading"),
                "paper_title": record.get("paper_title"),
                "original_filename": record.get("original_filename"),
                "tokens": tokens,
                "text": record["text"],
            }
        )

    _ = BM25Okapi(tokenized_corpus)

    return {
        "project_id": project_id,
        "project_slug": project_slug,
        "total_entries": len(entries),
        "entries": entries,
    }


def save_bm25_payload(output_path: str | Path, payload: dict) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)