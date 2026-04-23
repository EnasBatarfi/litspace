# This module defines functions to build system and user prompts for the LitSpace research assistant.

from __future__ import annotations


def build_system_prompt() -> str:
    return (
        "You are LitSpace, a grounded research assistant. "
        "Answer only from the provided project sources. "
        "Do not use outside knowledge. "
        "If the sources do not contain enough evidence to answer the question, "
        "respond with: 'Insufficient evidence in the provided sources.' "
        "Do not guess. "
        "Do not answer from background knowledge. "
        "Use inline citations like [S1], [S2]. "
        "Do not group citations like [S1, S2]. "
        "Write each citation separately, like [S1] [S2]. "
        "Only cite a source if it directly supports the statement."
    )


def build_user_prompt(query: str, hits: list[dict]) -> str:
    source_blocks = []

    for idx, hit in enumerate(hits, start=1):
        source_id = f"S{idx}"
        section = hit.get("section_heading") or "Unknown section"
        paper = hit.get("paper_title") or hit.get("original_filename") or f"paper-{hit['paper_id']}"
        pages = f"{hit['page_start']}-{hit['page_end']}"
        text = hit["text"].strip()

        source_blocks.append(
            f"[{source_id}]\n"
            f"Paper: {paper}\n"
            f"Section: {section}\n"
            f"Pages: {pages}\n"
            f"Text:\n{text}"
        )

    joined_sources = "\n\n".join(source_blocks)

    return (
        f"Question:\n{query}\n\n"
        f"Sources:\n{joined_sources}\n\n"
        "Instructions:\n"
        "1. Answer using only the provided sources.\n"
        "2. Use inline citations like [S1] or [S2]. Never group them as [S1, S2]; write [S1] [S2].\n"
        "3. If the sources do not answer the question, say exactly: "
        "'Insufficient evidence in the provided sources.'\n"
        "4. Do not guess.\n"
        "5. Do not use outside knowledge.\n"
        "6. Return only the answer text."
    )
