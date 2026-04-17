# This module implements the semantic retrieval functionality using ChromaDB.

from __future__ import annotations

import chromadb

from app.services.embedding.encoder import embed_texts
from app.services.indexing.chroma_indexer import get_collection_name
from app.utils.paths import get_chroma_persist_dir


def semantic_retrieve(
    project_slug: str,
    query: str,
    top_k: int = 10,
) -> list[dict]:
    client = chromadb.PersistentClient(path=str(get_chroma_persist_dir()))
    collection = client.get_collection(get_collection_name(project_slug))

    query_embedding = embed_texts([query], batch_size=1)[0]

    result = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    hits: list[dict] = []
    for idx, chunk_id in enumerate(ids):
        metadata = metadatas[idx] or {}
        hits.append(
            {
                "chunk_id": chunk_id,
                "paper_id": int(metadata["paper_id"]),
                "project_id": int(metadata["project_id"]),
                "project_slug": metadata["project_slug"],
                "chunk_index": int(metadata["chunk_index"]),
                "page_start": int(metadata["page_start"]),
                "page_end": int(metadata["page_end"]),
                "section_heading": metadata.get("section_heading") or None,
                "paper_title": metadata.get("paper_title") or None,
                "original_filename": metadata.get("original_filename") or None,
                "text": documents[idx],
                "distance": float(distances[idx]),
                "semantic_rank": idx + 1,
            }
        )

    return hits