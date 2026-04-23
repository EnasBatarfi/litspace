# This module provides functions for managing ChromaDB collections and adding chunk records to them.

from __future__ import annotations

import chromadb

from app.utils.paths import get_chroma_persist_dir


def get_collection_name(project_slug: str) -> str:
    return f"litspace__{project_slug}"


def delete_project_collection(project_slug: str) -> None:
    client = chromadb.PersistentClient(path=str(get_chroma_persist_dir()))
    collection_name = get_collection_name(project_slug)

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def recreate_project_collection(project_slug: str):
    client = chromadb.PersistentClient(path=str(get_chroma_persist_dir()))
    collection_name = get_collection_name(project_slug)

    delete_project_collection(project_slug)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def add_chunk_records_to_collection(collection, records: list[dict], embeddings) -> None:
    ids = [record["chunk_id"] for record in records]
    documents = [record["text"] for record in records]

    metadatas = []
    for record in records:
        metadatas.append(
            {
                "chunk_id": record["chunk_id"],
                "paper_id": int(record["paper_id"]),
                "project_id": int(record["project_id"]),
                "project_slug": record["project_slug"],
                "chunk_index": int(record["chunk_index"]),
                "page_start": int(record["page_start"]),
                "page_end": int(record["page_end"]),
                "section_heading": record.get("section_heading") or "",
                "paper_title": record.get("paper_title") or "",
                "original_filename": record.get("original_filename") or "",
            }
        )

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
