from __future__ import annotations

import csv
import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evaluation"
DATASET_CSV = EVAL_DIR / "datasets" / "questions.csv"
SUMMARIES_JSON = EVAL_DIR / "datasets" / "paper_summaries.json"
OUTPUTS_DIR = EVAL_DIR / "outputs"
ENV_PATH = EVAL_DIR / ".env"
ENV_EXAMPLE_PATH = EVAL_DIR / ".env.example"

PAPER_ALIASES = {
    "Progent": ["progent", "programmable privilege control"],
    "MCP-Secure": ["mcp-secure", "mcp secure", "runtime access control layer"],
    "AgentSpec": ["agentspec"],
    "Conseca": ["conseca", "contextual agent security"],
    "AgentGuardian": ["agentguardian"],
    "AgentArmor": ["agentarmor", "structured graph abstraction"],
    "ACE": ["ace", "abstract-concrete-execute", "security architecture for llm-integrated app systems"],
}

ORDINAL_WORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
}

CLARIFICATION_CUES = (
    "which paper",
    "which papers",
    "do you mean",
    "which one do you mean",
)

REFUSAL_CUES = (
    "outside the project",
    "outside the uploaded papers",
    "outside the uploaded sources",
    "outside the project sources",
    "i cannot answer that from the project",
    "i can't answer that from the project",
    "i can't answer that from the uploaded project papers",
    "not supported by the project sources",
    "not answerable from the project papers",
)
EXPLICIT_ALL_SCOPE_PHRASES = (
    "all papers",
    "all the papers",
    "each paper",
    "every paper",
    "all papers in this project",
    "each paper in this project",
    "every paper in this project",
)

ZERO_SHOT_SYSTEM_PROMPT = """You are answering user questions in a project about a small set of research papers.
You do not have access to the paper texts or retrieval results.
Use only the conversation itself.

Rules:
- If the request is ambiguous, ask a short clarification question.
- If the request is outside the project papers, refuse briefly.
- If you are unsure about exact paper-specific details, say so briefly instead of inventing them.
- Do not claim retrieval, quoted evidence, or document access.
"""

SUMMARY_FEW_SHOT_SYSTEM_PROMPT = """You are answering user questions in a project about a small set of research papers.
You are given short summary cards for relevant papers and a few demonstrations.
Use only the provided summary cards and the conversation itself.

Rules:
- If the request is ambiguous, ask a short clarification question.
- If the request is outside the project papers, refuse briefly.
- If the summary cards are insufficient for an exact detail, say so briefly instead of inventing it.
- Do not claim retrieval, quoted evidence, or full document access.
"""

SUMMARY_FEW_SHOT_DEMONSTRATIONS = """Example 1
User request:
Summarize the paper.

Assistant:
Which paper do you want summarized?

Example 2
Relevant summaries:
Paper: Progent
Goal: Controls unsafe LLM-agent tool use through programmable privilege control.
Method: Defines runtime policies over tool calls and arguments using a structured policy language enforced deterministically.
Key contribution: Applies least-privilege style control to agent tool usage at runtime.
Main limitation: Still depends on policy coverage and correct policy specification.

User request:
What is Progent?

Assistant:
Progent is a paper about controlling unsafe LLM-agent tool use with programmable runtime privilege policies.

Example 3
Relevant summaries:
Paper: Progent
Goal: Controls unsafe LLM-agent tool use through programmable privilege control.
Method: Defines runtime policies over tool calls and arguments using a structured policy language enforced deterministically.
Key contribution: Applies least-privilege style control to agent tool usage at runtime.
Main limitation: Still depends on policy coverage and correct policy specification.

Paper: MCP-Secure
Goal: Improves safety of MCP-based tool access for LLM systems.
Method: Uses scoped access, read-only defaults, and approval-gated privilege elevation for tool interactions.
Key contribution: Adds host-side control over tool permissions and session behavior.
Main limitation: May still trade off convenience and flexibility for stronger control.

User request:
Compare Progent and MCP-Secure.

Assistant:
Both focus on runtime control of unsafe tool use, but Progent emphasizes programmable privilege policies, while MCP-Secure emphasizes scoped and approval-gated MCP access control.

Example 4
User request:
What is the weather in Tokyo today?

Assistant:
I cannot answer that from the project papers because it is outside the project scope.
"""


def load_eval_env() -> None:
    source = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    load_dotenv(source, override=True)


load_eval_env()

API_BASE = os.environ["LITSPACE_API_BASE"].rstrip("/")
PROJECT_ID = int(os.environ["LITSPACE_EVAL_PROJECT_ID"])
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

ZERO_SHOT_MODEL = os.environ.get("ZERO_SHOT_MODEL", "gpt-5.4-mini")
SUMMARY_FEW_SHOT_MODEL = os.environ.get("SUMMARY_FEW_SHOT_MODEL", "gpt-5.4-mini")

LITSPACE_TOP_K = int(os.environ.get("LITSPACE_TOP_K", "6"))
LITSPACE_MAX_OUTPUT_TOKENS = int(os.environ.get("LITSPACE_MAX_OUTPUT_TOKENS", "500"))
LITSPACE_TEMPERATURE = float(os.environ.get("LITSPACE_TEMPERATURE", "0.1"))
RETRIEVE_TOP_K = int(os.environ.get("RETRIEVE_TOP_K", "5"))

OPENAI_INPUT_COST_PER_1M = float(os.environ.get("OPENAI_INPUT_COST_PER_1M", "0"))
OPENAI_OUTPUT_COST_PER_1M = float(os.environ.get("OPENAI_OUTPUT_COST_PER_1M", "0"))


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def parse_alias_groups(value: str) -> list[list[str]]:
    groups: list[list[str]] = []
    for raw_group in split_pipe(value):
        aliases = [alias.strip().lower() for alias in raw_group.split(";") if alias.strip()]
        if aliases:
            groups.append(aliases)
    return groups


def load_questions() -> list[dict]:
    rows: list[dict] = []
    with DATASET_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["turns_json"] = json.loads(row["turns_json"])
            row["selected_papers"] = split_pipe(row["selected_papers"])
            row["expected_papers"] = split_pipe(row["expected_papers"])
            row["required_points"] = split_pipe(row["required_points"])
            row["expected_support_sections"] = parse_alias_groups(row["expected_support_sections"])
            row["should_clarify"] = str(row["should_clarify"]).strip() == "1"
            row["should_refuse"] = str(row["should_refuse"]).strip() == "1"
            rows.append(row)
    return rows


def load_paper_summaries() -> dict:
    with SUMMARIES_JSON.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def canonical_paper_name(raw_name: str) -> str:
    lowered = raw_name.lower()
    normalized = normalize_text(raw_name)
    for canonical, hints in PAPER_ALIASES.items():
        for hint in hints:
            if hint.lower() in lowered or normalize_text(hint) in normalized:
                return canonical
    return raw_name.strip()


def fetch_project_papers() -> list[dict]:
    response = requests.get(f"{API_BASE}/projects/{PROJECT_ID}/papers", timeout=60)
    response.raise_for_status()
    return response.json()


def build_project_maps(project_papers: list[dict]) -> tuple[dict[str, int], list[str], list[int]]:
    alias_to_id: dict[str, int] = {}
    visible_project_papers: list[str] = []
    default_order_ids: list[int] = []

    for paper in project_papers:
        paper_id = int(paper["id"])
        raw_name = paper.get("paper_title") or paper.get("title") or paper.get("original_filename") or f"Paper {paper_id}"
        canonical = canonical_paper_name(raw_name)
        alias_to_id[canonical] = paper_id
        visible_project_papers.append(canonical)
        default_order_ids.append(paper_id)

    return alias_to_id, visible_project_papers, default_order_ids


def parse_visible_order(selected_papers: list[str]) -> list[str]:
    ordered: list[tuple[int, str]] = []
    for item in selected_papers:
        match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", item)
        if match:
            ordered.append((int(match.group(1)), match.group(2).strip()))
    return [name for _, name in sorted(ordered)]


def selected_named_papers(row: dict) -> list[str]:
    names: list[str] = []
    for item in row["selected_papers"]:
        if re.match(r"^\s*\d+\s+", item):
            continue
        canonical = canonical_paper_name(item)
        if canonical in PAPER_ALIASES and canonical not in names:
            names.append(canonical)
    return names


def build_selected_ids(row: dict, alias_to_id: dict[str, int]) -> list[int]:
    ids: list[int] = []
    for paper_name in selected_named_papers(row):
        if paper_name in alias_to_id:
            ids.append(alias_to_id[paper_name])
    return ids


def build_paper_order_ids(row: dict, alias_to_id: dict[str, int], default_order_ids: list[int]) -> list[int]:
    visible_names = parse_visible_order(row["selected_papers"])
    if not visible_names:
        return default_order_ids
    ordered_ids = [alias_to_id[name] for name in visible_names if name in alias_to_id]
    return ordered_ids or default_order_ids


def mentioned_papers_in_turns(turns_json: list[str]) -> list[str]:
    text = " ".join(turns_json).lower()
    found: list[str] = []
    for canonical, hints in PAPER_ALIASES.items():
        for hint in hints:
            if re.search(rf"\b{re.escape(hint.lower())}\b", text):
                if canonical not in found:
                    found.append(canonical)
                break
    return found


def ordinal_targets_from_turns(turns_json: list[str], visible_names: list[str]) -> list[str]:
    if not visible_names:
        return []

    indices: set[int] = set()
    for turn in turns_json:
        lowered = turn.lower().strip()
        for word, index in ORDINAL_WORDS.items():
            if re.search(rf"\b{word}\b", lowered):
                indices.add(index)
        for match in re.finditer(r"\bpaper\s+(\d+)\b", lowered):
            indices.add(int(match.group(1)))
        if re.fullmatch(r"\d+", lowered):
            indices.add(int(lowered))

    resolved: list[str] = []
    for index in sorted(indices):
        if 1 <= index <= len(visible_names):
            resolved.append(visible_names[index - 1])
    return resolved


def infer_focus_papers(row: dict, visible_project_papers: list[str]) -> list[str]:
    if row["should_clarify"] or row["should_refuse"]:
        return []

    explicit_mentions = mentioned_papers_in_turns(row["turns_json"])
    if explicit_mentions:
        return explicit_mentions

    named_hints = selected_named_papers(row)
    if named_hints:
        return named_hints

    ordinal_hints = ordinal_targets_from_turns(row["turns_json"], parse_visible_order(row["selected_papers"]))
    if ordinal_hints:
        return ordinal_hints

    joined_turns = " ".join(turn.lower() for turn in row["turns_json"])
    if any(phrase in joined_turns for phrase in EXPLICIT_ALL_SCOPE_PHRASES):
        return visible_project_papers

    return []


def build_summary_context(row: dict, visible_project_papers: list[str], summaries: dict) -> tuple[str, list[str]]:
    focus_papers = infer_focus_papers(row, visible_project_papers)
    if not focus_papers:
        return "", []

    parts: list[str] = []
    for paper in focus_papers:
        summary = summaries.get(paper)
        if not summary:
            continue
        parts.append(
            "\n".join(
                [
                    f"Paper: {paper}",
                    f"Goal: {summary.get('goal', '')}",
                    f"Method: {summary.get('method', '')}",
                    f"Key contribution: {summary.get('key_contribution', '')}",
                    f"Main limitation: {summary.get('main_limitation', '')}",
                ]
            )
        )
    if not parts:
        return "", []
    return "Relevant summaries:\n\n" + "\n\n".join(parts), focus_papers


def create_chat() -> int | None:
    response = requests.post(f"{API_BASE}/projects/{PROJECT_ID}/chats", json={}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    return payload.get("id") or payload.get("chat_id")


def ask_litspace(query: str, chat_id: int | None, selected_ids: list[int], paper_order_ids: list[int]) -> dict:
    payload = {
        "query": query,
        "top_k": LITSPACE_TOP_K,
        "max_output_tokens": LITSPACE_MAX_OUTPUT_TOKENS,
        "temperature": LITSPACE_TEMPERATURE,
        "selected_paper_ids": selected_ids,
        "paper_order_ids": paper_order_ids,
    }
    if chat_id is not None:
        payload["chat_id"] = chat_id
    response = requests.post(f"{API_BASE}/projects/{PROJECT_ID}/ask", json=payload, timeout=180)
    response.raise_for_status()
    return response.json()


def build_retrieval_query(turns_json: list[str]) -> str:
    if len(turns_json) <= 1:
        return turns_json[-1]
    return "\n".join(
        [f"Turn {index}: {turn}" for index, turn in enumerate(turns_json, start=1)]
    )


def retrieve_litspace(query: str, selected_ids: list[int], paper_order_ids: list[int]) -> dict:
    payload = {
        "query": query,
        "top_k": RETRIEVE_TOP_K,
        "selected_paper_ids": selected_ids,
        "paper_order_ids": paper_order_ids,
    }
    response = requests.post(f"{API_BASE}/projects/{PROJECT_ID}/retrieve", json=payload, timeout=180)
    response.raise_for_status()
    return response.json()


def classify_answer_behavior(answer: str) -> str:
    lowered = (answer or "").lower()
    if any(cue in lowered for cue in CLARIFICATION_CUES):
        return "clarify"
    if any(cue in lowered for cue in REFUSAL_CUES):
        return "refuse"
    return "answer"


def resolve_behavior_label(answer: str, action: str | None = None) -> str:
    if action in {"answer", "clarify", "refuse"}:
        return action
    return classify_answer_behavior(answer)


def clarification_accuracy(answer: str, row: dict, *, action: str | None = None) -> int | str:
    if not row["should_clarify"]:
        return ""
    return int(resolve_behavior_label(answer, action) == "clarify")


def refusal_accuracy(answer: str, row: dict, *, action: str | None = None) -> int | str:
    if not row["should_refuse"]:
        return ""
    return int(resolve_behavior_label(answer, action) == "refuse")


def paper_title_matches(hit_title: str, expected_paper: str) -> bool:
    canonical_hit = canonical_paper_name(hit_title or "")
    return canonical_hit == expected_paper


def compute_paper_hit_at_5(retrieve_hits: list[dict], expected_papers: list[str]) -> int | str:
    if not expected_papers:
        return ""
    for hit in retrieve_hits[:5]:
        title = hit.get("paper_title") or hit.get("title") or hit.get("original_filename") or ""
        if any(paper_title_matches(title, expected_paper) for expected_paper in expected_papers):
            return 1
    return 0


def compute_paper_recall_at_5(retrieve_hits: list[dict], expected_papers: list[str]) -> float | str:
    if not expected_papers:
        return ""
    matched: set[str] = set()
    for hit in retrieve_hits[:5]:
        title = hit.get("paper_title") or hit.get("title") or hit.get("original_filename") or ""
        for expected_paper in expected_papers:
            if paper_title_matches(title, expected_paper):
                matched.add(expected_paper)
    return len(matched) / len(expected_papers)


def compute_paper_mrr_at_5(retrieve_hits: list[dict], expected_papers: list[str]) -> float | str:
    if not expected_papers:
        return ""
    for rank, hit in enumerate(retrieve_hits[:5], start=1):
        title = hit.get("paper_title") or hit.get("title") or hit.get("original_filename") or ""
        if any(paper_title_matches(title, expected_paper) for expected_paper in expected_papers):
            return 1.0 / rank
    return 0.0


def section_group_matches(hit_section: str, alias_group: list[str]) -> bool:
    lowered = (hit_section or "").lower()
    return any(alias in lowered for alias in alias_group)


def compute_section_hit_at_5(retrieve_hits: list[dict], expected_groups: list[list[str]]) -> int | str:
    if not expected_groups:
        return ""
    for hit in retrieve_hits[:5]:
        section = hit.get("section_heading") or ""
        if any(section_group_matches(section, alias_group) for alias_group in expected_groups):
            return 1
    return 0


def compute_section_recall_at_5(retrieve_hits: list[dict], expected_groups: list[list[str]]) -> float | str:
    if not expected_groups:
        return ""
    matched = 0
    for alias_group in expected_groups:
        if any(section_group_matches(hit.get("section_heading") or "", alias_group) for hit in retrieve_hits[:5]):
            matched += 1
    return matched / len(expected_groups)


def estimate_baseline_cost(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    input_cost = (input_tokens / 1_000_000) * OPENAI_INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OPENAI_OUTPUT_COST_PER_1M
    return input_cost + output_cost


def run_prompt_baseline(
    client: OpenAI,
    model_name: str,
    system_prompt: str,
    row: dict,
    context_block: str = "",
) -> dict:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context_block:
        messages.append({"role": "system", "content": context_block})

    turn_records: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0
    final_answer = ""

    start_time = time.perf_counter()

    for turn in row["turns_json"]:
        call_start = time.perf_counter()
        response = client.responses.create(
            model=model_name,
            input=messages + [{"role": "user", "content": turn}],
        )
        call_latency = time.perf_counter() - call_start

        final_answer = response.output_text.strip()
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
        output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None

        if input_tokens is not None:
            total_input_tokens += input_tokens
        if output_tokens is not None:
            total_output_tokens += output_tokens

        turn_records.append(
            {
                "user_turn": turn,
                "assistant_answer": final_answer,
                "latency_sec": round(call_latency, 6),
            }
        )

        messages.extend(
            [
                {"role": "user", "content": turn},
                {"role": "assistant", "content": final_answer},
            ]
        )

    latency_sec = time.perf_counter() - start_time
    total_tokens = None
    if total_input_tokens or total_output_tokens:
        total_tokens = total_input_tokens + total_output_tokens

    return {
        "answer": final_answer,
        "action": classify_answer_behavior(final_answer),
        "answer_behavior": classify_answer_behavior(final_answer),
        "turn_records": turn_records,
        "latency_sec": round(latency_sec, 6),
        "input_tokens": total_input_tokens or None,
        "output_tokens": total_output_tokens or None,
        "total_tokens": total_tokens,
        "cost_usd": estimate_baseline_cost(total_input_tokens or None, total_output_tokens or None),
    }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    questions = load_questions()
    summaries = load_paper_summaries()
    print(f"[evaluation] loaded {len(questions)} questions")
    print(f"[evaluation] loaded paper summaries from {SUMMARIES_JSON}")

    project_papers = fetch_project_papers()
    alias_to_id, visible_project_papers, default_order_ids = build_project_maps(project_papers)
    print(f"[evaluation] fetched {len(project_papers)} project papers for project_id={PROJECT_ID}")

    litspace_outputs: list[dict] = []
    litspace_direct_rows: list[dict] = []

    print("[evaluation] running litspace_rag")
    for row in questions:
        print(f"[evaluation] litspace_rag {row['id']} {row['category']}")
        selected_ids = build_selected_ids(row, alias_to_id)
        paper_order_ids = build_paper_order_ids(row, alias_to_id, default_order_ids)
        chat_id = create_chat() if len(row["turns_json"]) > 1 else None

        turn_records: list[dict] = []
        last_answer: dict | None = None
        answer_latency_total = 0.0

        for turn in row["turns_json"]:
            call_start = time.perf_counter()
            last_answer = ask_litspace(turn, chat_id, selected_ids, paper_order_ids)
            call_latency = time.perf_counter() - call_start
            answer_latency_total += call_latency

            turn_records.append(
                {
                    "user_turn": turn,
                    "assistant_answer": last_answer.get("answer", ""),
                    "latency_sec": round(call_latency, 6),
                    "insufficient_evidence": last_answer.get("insufficient_evidence"),
                }
            )

        retrieval_query = build_retrieval_query(row["turns_json"])
        retrieve_start = time.perf_counter()
        retrieve_payload = retrieve_litspace(retrieval_query, selected_ids, paper_order_ids)
        retrieve_latency_sec = time.perf_counter() - retrieve_start
        retrieve_hits = retrieve_payload.get("hits", [])

        answer_text = last_answer.get("answer", "") if last_answer else ""
        answer_action = (last_answer or {}).get("action")
        answer_behavior = resolve_behavior_label(answer_text, answer_action)
        backend_usage = (last_answer or {}).get("usage") or {}
        backend_timing = (last_answer or {}).get("timing") or {}

        litspace_outputs.append(
            {
                "id": row["id"],
                "system_name": "litspace_rag",
                "category": row["category"],
                "question": row["question"],
                "turns_json": row["turns_json"],
                "selected_papers": row["selected_papers"],
                "target_scope": row["target_scope"],
                "expected_papers": row["expected_papers"],
                "answer": answer_text,
                "action": answer_action,
                "answer_behavior": answer_behavior,
                "turn_records": turn_records,
                "used_sources": (last_answer or {}).get("used_sources", []),
                "retrieve_hits": retrieve_hits,
                "retrieval_query": retrieval_query,
                "retrieval_hits_count": (last_answer or {}).get("retrieval_hits_count"),
                "insufficient_evidence": (last_answer or {}).get("insufficient_evidence"),
                "latency_sec": round(answer_latency_total, 6),
                "retrieve_latency_sec": round(retrieve_latency_sec, 6),
                "backend_total_latency_sec": backend_timing.get("total_latency_sec"),
                "backend_retrieval_latency_sec": backend_timing.get("retrieval_latency_sec"),
                "backend_generation_latency_sec": backend_timing.get("generation_latency_sec"),
                "input_tokens": backend_usage.get("input_tokens"),
                "output_tokens": backend_usage.get("output_tokens"),
                "total_tokens": backend_usage.get("total_tokens"),
                "provider": backend_usage.get("llm_provider"),
                "model": backend_usage.get("llm_model"),
                "cost_usd": None,
            }
        )

        litspace_direct_rows.append(
            {
                "id": row["id"],
                "paper_hit_at_5": compute_paper_hit_at_5(retrieve_hits, row["expected_papers"]),
                "paper_recall_at_5": compute_paper_recall_at_5(retrieve_hits, row["expected_papers"]),
                "section_hit_at_5": compute_section_hit_at_5(retrieve_hits, row["expected_support_sections"]),
                "section_recall_at_5": compute_section_recall_at_5(retrieve_hits, row["expected_support_sections"]),
                "paper_mrr_at_5": compute_paper_mrr_at_5(retrieve_hits, row["expected_papers"]),
                "clarification_accuracy": clarification_accuracy(answer_text, row, action=answer_action),
                "refusal_accuracy": refusal_accuracy(answer_text, row, action=answer_action),
            }
        )

    write_jsonl(OUTPUTS_DIR / "litspace_outputs.jsonl", litspace_outputs)
    write_csv(
        OUTPUTS_DIR / "direct_metrics_litspace.csv",
        litspace_direct_rows,
        [
            "id",
            "paper_hit_at_5",
            "paper_recall_at_5",
            "section_hit_at_5",
            "section_recall_at_5",
            "paper_mrr_at_5",
            "clarification_accuracy",
            "refusal_accuracy",
        ],
    )
    print(f"[evaluation] wrote {OUTPUTS_DIR / 'litspace_outputs.jsonl'}")
    print(f"[evaluation] wrote {OUTPUTS_DIR / 'direct_metrics_litspace.csv'}")

    client = OpenAI(api_key=OPENAI_API_KEY)
    zero_outputs: list[dict] = []
    zero_direct_rows: list[dict] = []
    summary_outputs: list[dict] = []
    summary_direct_rows: list[dict] = []

    print("[evaluation] running zero_shot and summary_few_shot")
    for row in questions:
        print(f"[evaluation] baselines {row['id']} {row['category']}")
        summary_context, focus_papers = build_summary_context(row, visible_project_papers, summaries)

        zero_result = run_prompt_baseline(
            client=client,
            model_name=ZERO_SHOT_MODEL,
            system_prompt=ZERO_SHOT_SYSTEM_PROMPT,
            row=row,
            context_block="",
        )
        zero_outputs.append(
            {
                "id": row["id"],
                "system_name": "zero_shot",
                "category": row["category"],
                "question": row["question"],
                "turns_json": row["turns_json"],
                "answer": zero_result["answer"],
                "action": zero_result["action"],
                "answer_behavior": zero_result["answer_behavior"],
                "turn_records": zero_result["turn_records"],
                "latency_sec": zero_result["latency_sec"],
                "input_tokens": zero_result["input_tokens"],
                "output_tokens": zero_result["output_tokens"],
                "total_tokens": zero_result["total_tokens"],
                "cost_usd": zero_result["cost_usd"],
                "model": ZERO_SHOT_MODEL,
            }
        )
        zero_direct_rows.append(
            {
                "id": row["id"],
                "clarification_accuracy": clarification_accuracy(zero_result["answer"], row, action=zero_result["action"]),
                "refusal_accuracy": refusal_accuracy(zero_result["answer"], row, action=zero_result["action"]),
            }
        )

        summary_context_block = SUMMARY_FEW_SHOT_DEMONSTRATIONS
        if summary_context:
            summary_context_block = summary_context_block + "\n\n" + summary_context

        summary_result = run_prompt_baseline(
            client=client,
            model_name=SUMMARY_FEW_SHOT_MODEL,
            system_prompt=SUMMARY_FEW_SHOT_SYSTEM_PROMPT,
            row=row,
            context_block=summary_context_block,
        )
        summary_outputs.append(
            {
                "id": row["id"],
                "system_name": "summary_few_shot",
                "category": row["category"],
                "question": row["question"],
                "turns_json": row["turns_json"],
                "focus_papers": focus_papers,
                "summary_context": summary_context,
                "answer": summary_result["answer"],
                "action": summary_result["action"],
                "answer_behavior": summary_result["answer_behavior"],
                "turn_records": summary_result["turn_records"],
                "latency_sec": summary_result["latency_sec"],
                "input_tokens": summary_result["input_tokens"],
                "output_tokens": summary_result["output_tokens"],
                "total_tokens": summary_result["total_tokens"],
                "cost_usd": summary_result["cost_usd"],
                "model": SUMMARY_FEW_SHOT_MODEL,
            }
        )
        summary_direct_rows.append(
            {
                "id": row["id"],
                "clarification_accuracy": clarification_accuracy(summary_result["answer"], row, action=summary_result["action"]),
                "refusal_accuracy": refusal_accuracy(summary_result["answer"], row, action=summary_result["action"]),
            }
        )

    write_jsonl(OUTPUTS_DIR / "zero_shot_outputs.jsonl", zero_outputs)
    write_jsonl(OUTPUTS_DIR / "summary_few_shot_outputs.jsonl", summary_outputs)
    write_csv(
        OUTPUTS_DIR / "direct_metrics_zero_shot.csv",
        zero_direct_rows,
        ["id", "clarification_accuracy", "refusal_accuracy"],
    )
    write_csv(
        OUTPUTS_DIR / "direct_metrics_summary_few_shot.csv",
        summary_direct_rows,
        ["id", "clarification_accuracy", "refusal_accuracy"],
    )

    print(f"[evaluation] wrote {OUTPUTS_DIR / 'zero_shot_outputs.jsonl'}")
    print(f"[evaluation] wrote {OUTPUTS_DIR / 'summary_few_shot_outputs.jsonl'}")
    print(f"[evaluation] wrote {OUTPUTS_DIR / 'direct_metrics_zero_shot.csv'}")
    print(f"[evaluation] wrote {OUTPUTS_DIR / 'direct_metrics_summary_few_shot.csv'}")
    print("[evaluation] run complete")


if __name__ == "__main__":
    main()
