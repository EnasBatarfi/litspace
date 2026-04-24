# This module defines functions to build system and user prompts for the LitSpace research assistant.

from __future__ import annotations


def build_system_prompt() -> str:
    return (
        "You are LitSpace, a grounded research assistant. "
        "Answer only from the provided project sources. "
        "Do not use outside knowledge. "
        "If the sources do not contain enough evidence to answer any part of the question, "
        "respond with: 'Insufficient evidence in the provided sources.' "
        "If the sources support only part of the request, answer the supported part and mention the missing support only when it materially changes the answer. "
        "Do not append a standalone 'Unsupported:' or 'Insufficient evidence' addendum after an otherwise supported answer. "
        "Do not guess. "
        "Do not answer from background knowledge. "
        "Use inline citations like [S1], [S2]. "
        "Do not group citations like [S1, S2]. "
        "Write each citation separately, like [S1] [S2]. "
        "Only cite a source if it directly supports the statement."
    )


def build_user_prompt(
    query: str,
    hits: list[dict],
    *,
    recent_messages: list[dict[str, str]] | None = None,
    target_papers: list[str] | None = None,
    answer_plan: dict[str, str] | None = None,
) -> str:
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
    history_block = ""
    if recent_messages:
        history_lines = "\n".join(
            f"{message['role'].title()}: {message['content']}"
            for message in recent_messages
        )
        history_block = (
            "Recent chat context (reference only; current question and sources win):\n"
            f"{history_lines}\n\n"
        )

    scope_block = ""
    if target_papers:
        scope_lines = "\n".join(f"- {paper}" for paper in target_papers)
        scope_block = f"Resolved paper scope:\n{scope_lines}\n\n"

    answer_plan_block = ""
    if answer_plan:
        answer_plan_block = (
            "Answer plan:\n"
            f"- Request type: {answer_plan['request_type']}\n"
            f"- Response mode: {answer_plan['response_mode']}\n"
            f"- Organize by: {answer_plan['organize_by']}\n"
            f"- Prefer markdown table: {answer_plan['prefer_table']}\n\n"
        )

    return (
        f"Question:\n{query}\n\n"
        f"{scope_block}"
        f"{history_block}"
        f"{answer_plan_block}"
        f"Sources:\n{joined_sources}\n\n"
        "Instructions:\n"
        "1. Answer using only the provided sources.\n"
        "2. Use inline citations like [S1] or [S2]. Never group them as [S1, S2]; write [S1] [S2].\n"
        "3. If none of the sources support any part of the question, say exactly: "
        "'Insufficient evidence in the provided sources.'\n"
        "4. Do not guess.\n"
        "5. Do not use outside knowledge.\n"
        "6. If a paper scope is provided, stay within that scope.\n"
        "7. If the answer plan says comparison and multiple papers are supported, you may use a compact markdown table.\n"
        "8. If the scope covers multiple papers, organize the answer by paper or comparison axis and avoid collapsing everything to one paper.\n"
        "9. If the retrieved evidence only supports some of the scoped papers, return a partial answer and mention missing paper coverage only when it is material to the request.\n"
        "10. If requested fields such as objective, method, results, or limitations are only partially supported, fill the supported fields and mention the unsupported field inline rather than as a standalone disclaimer.\n"
        "11. If the answer plan says quote extraction, provide short exact quotes from the sources with quotation marks, organize them by paper, and do not paraphrase the quoted sentence.\n"
        "12. Return only the answer text."
    )
