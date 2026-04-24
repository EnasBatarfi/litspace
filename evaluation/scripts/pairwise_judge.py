from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evaluation"

env_path = EVAL_DIR / ".env"
env_example_path = EVAL_DIR / ".env.example"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    load_dotenv(env_example_path, override=True)

DATASET_CSV = EVAL_DIR / "datasets" / "questions.csv"
SUMMARIES_JSON = EVAL_DIR / "datasets" / "paper_summaries.json"
OUTPUTS_DIR = EVAL_DIR / "outputs"

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gpt-5.4")
MAX_JUDGE_ATTEMPTS = 3
REQUIRED_PAIRWISE_KEYS = {"winner", "short_reason"}
VALID_WINNERS = {"A", "B", "tie"}


def load_questions() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with DATASET_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["turns_json"] = json.loads(row["turns_json"])
            row["required_points"] = [x for x in row["required_points"].split("|") if x]
            row["should_clarify"] = str(row["should_clarify"]).strip() == "1"
            row["should_refuse"] = str(row["should_refuse"]).strip() == "1"
            rows[row["id"]] = row
    return rows


def read_jsonl(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_paper_summaries() -> dict:
    with SUMMARIES_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_summary_background(summaries: dict) -> str:
    lines = [
        "Benchmark paper summaries (background only; reference answer and required points override this map):"
    ]
    for paper, summary in summaries.items():
        goal = summary.get("goal", "")
        method = summary.get("method", "")
        lines.append(f"- {paper}: goal={goal} method={method}")
    return "\n".join(lines)


def format_litspace_sources(sources: list[dict]) -> str:
    if not sources:
        return "NONE"
    parts: list[str] = []
    for source in sources:
        parts.append(
            f"Paper: {source.get('paper_title', '')}\n"
            f"Section: {source.get('section_heading', '')}\n"
            f"Excerpt: {source.get('excerpt', '')}"
        )
    return "\n\n---\n\n".join(parts)


def format_support(row: dict) -> str:
    if row.get("used_sources"):
        return format_litspace_sources(row["used_sources"])
    if row.get("summary_context"):
        return row["summary_context"]
    return "NONE"


def build_prompt(
    qrow: dict,
    row_a: dict,
    system_a: str,
    row_b: dict,
    system_b: str,
    summary_background: str,
) -> str:
    if qrow["should_clarify"]:
        expected_behavior = "clarify"
    elif qrow["should_refuse"]:
        expected_behavior = "refuse"
    else:
        expected_behavior = "answer"

    return f"""
{summary_background}

Question:
{qrow["question"]}

Turns:
{json.dumps(qrow["turns_json"], ensure_ascii=False)}

Expected behavior:
{expected_behavior}

Reference answer:
{qrow["reference_answer"]}

Required points:
{qrow["required_points"]}

Answer A ({system_a}):
{row_a["answer"]}

Support A:
{format_support(row_a)}

Answer B ({system_b}):
{row_b["answer"]}

Support B:
{format_support(row_b)}

Decision rules:
- Prefer the answer that better matches the benchmark item's expected behavior and required points.
- Do not prefer extra detail unless it is also relevant and supported.
- Do not assume a retrieval-based system should win automatically.
- Penalize unnecessary clarification on answer rows.
- Penalize failure to clarify on ambiguity rows.
- Penalize failure to refuse on refusal rows.
- Prefer the answer that is more appropriate, better scoped, less likely to overclaim, and more useful for the benchmark item.
- A cautious partial answer may beat a more detailed but unsupported answer.

Tie rule:
- Use "tie" when both answers are similarly good, similarly weak, or differ mostly in style without a clear benchmark advantage.
- Do not force a winner when differences are minor.

Return JSON with:
- winner: one of ["A","B","tie"]
- short_reason: string
""".strip()


def parse_pairwise_response(text: str) -> dict:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    missing = REQUIRED_PAIRWISE_KEYS - set(obj)
    if missing:
        raise ValueError(f"missing keys: {sorted(missing)}")
    if obj["winner"] not in VALID_WINNERS:
        raise ValueError(f"invalid winner: {obj['winner']}")
    if not isinstance(obj["short_reason"], str) or not obj["short_reason"].strip():
        raise ValueError("short_reason must be a non-empty string")
    return obj


def request_pairwise_judgment(
    client: OpenAI,
    *,
    pairwise_system: str,
    prompt: str,
    label: str,
) -> dict:
    last_error: str | None = None
    last_text = ""

    for attempt in range(1, MAX_JUDGE_ATTEMPTS + 1):
        response = client.responses.create(
            model=JUDGE_MODEL,
            input=[
                {"role": "system", "content": pairwise_system},
                {"role": "user", "content": prompt},
            ],
        )
        last_text = response.output_text.strip()
        try:
            return parse_pairwise_response(last_text)
        except ValueError as exc:
            last_error = str(exc)
            print(f"[evaluation] retry {label} attempt={attempt} reason={last_error}")

    raise RuntimeError(
        f"Pairwise judge returned invalid JSON for {label} after {MAX_JUDGE_ATTEMPTS} attempts: {last_error}\nRaw output: {last_text}"
    )


def convert_reverse_winner(winner: str) -> str:
    if winner == "A":
        return "B"
    if winner == "B":
        return "A"
    return "tie"


def compare_pair(
    client: OpenAI,
    questions: dict[str, dict],
    pairwise_system: str,
    summary_background: str,
    rows_a: dict[str, dict],
    rows_b: dict[str, dict],
    system_a: str,
    system_b: str,
    reverse_rows_a: dict[str, dict],
    reverse_rows_b: dict[str, dict],
    output_path: Path,
) -> None:
    out: list[dict] = []
    print(f"[evaluation] pairwise compare {system_a} vs {system_b}")

    for qid, qrow in questions.items():
        print(f"[evaluation] pairwise {system_a} vs {system_b} {qid}")
        prompt_forward = build_prompt(
            qrow,
            rows_a[qid],
            system_a,
            rows_b[qid],
            system_b,
            summary_background,
        )
        prompt_reverse = build_prompt(
            qrow,
            reverse_rows_a[qid],
            system_b,
            reverse_rows_b[qid],
            system_a,
            summary_background,
        )
        forward = request_pairwise_judgment(
            client,
            pairwise_system=pairwise_system,
            prompt=prompt_forward,
            label=f"{system_a}_vs_{system_b}:{qid}:forward",
        )
        reverse = request_pairwise_judgment(
            client,
            pairwise_system=pairwise_system,
            prompt=prompt_reverse,
            label=f"{system_a}_vs_{system_b}:{qid}:reverse",
        )

        reverse_winner = convert_reverse_winner(reverse["winner"])
        if forward["winner"] == reverse_winner:
            winner = forward["winner"]
            short_reason = forward["short_reason"]
        else:
            winner = "tie"
            short_reason = (
                "Forward and reverse pairwise judgments disagreed after A/B swapping, so this comparison was marked as tie."
            )

        out.append(
            {
                "id": qid,
                "winner": winner,
                "short_reason": short_reason,
                "system_a": system_a,
                "system_b": system_b,
                "forward_winner": forward["winner"],
                "reverse_winner": reverse_winner,
            }
        )

    write_jsonl(output_path, out)
    print(f"[evaluation] wrote {output_path}")


def main() -> None:
    print("[evaluation] starting pairwise_judge")
    client = OpenAI(api_key=OPENAI_API_KEY)
    questions = load_questions()
    summary_background = format_summary_background(load_paper_summaries())

    pairwise_system = """You are a strict evaluator comparing two answers to the same research-paper question.
Use only the provided question, turns, expected behavior, reference answer, required points, and per-answer support if given.
Do not use outside knowledge.
Use the summary background only as lightweight calibration context.
Reference answer and required points override the summary background if they conflict.
Return valid JSON only.
"""

    litspace = read_jsonl(OUTPUTS_DIR / "litspace_outputs.jsonl")
    zero = read_jsonl(OUTPUTS_DIR / "zero_shot_outputs.jsonl")
    summary = read_jsonl(OUTPUTS_DIR / "summary_few_shot_outputs.jsonl")

    compare_pair(
        client=client,
        questions=questions,
        pairwise_system=pairwise_system,
        summary_background=summary_background,
        rows_a=litspace,
        rows_b=zero,
        system_a="litspace_rag",
        system_b="zero_shot",
        reverse_rows_a=zero,
        reverse_rows_b=litspace,
        output_path=OUTPUTS_DIR / "pairwise_litspace_vs_zero_shot.jsonl",
    )
    compare_pair(
        client=client,
        questions=questions,
        pairwise_system=pairwise_system,
        summary_background=summary_background,
        rows_a=litspace,
        rows_b=summary,
        system_a="litspace_rag",
        system_b="summary_few_shot",
        reverse_rows_a=summary,
        reverse_rows_b=litspace,
        output_path=OUTPUTS_DIR / "pairwise_litspace_vs_summary_few_shot.jsonl",
    )
    print("[evaluation] pairwise_judge complete")


if __name__ == "__main__":
    main()
