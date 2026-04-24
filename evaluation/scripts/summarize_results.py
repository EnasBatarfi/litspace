from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evaluation"
DATASET_CSV = EVAL_DIR / "datasets" / "questions.csv"
OUTPUTS_DIR = EVAL_DIR / "outputs"
RESULTS_DIR = EVAL_DIR / "results"


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path):
    rows = {}
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["id"]] = row
    return rows


def load_dataset_rows():
    rows = {}
    with DATASET_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["should_clarify"] = str(row["should_clarify"]).strip() == "1"
            row["should_refuse"] = str(row["should_refuse"]).strip() == "1"
            rows[row["id"]] = row
    return rows


def load_categories():
    cats = {}
    with DATASET_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cats[row["id"]] = row["category"]
    return cats


def avg(values):
    vals = [v for v in values if v not in ("", None)]
    vals = [float(v) for v in vals]
    return mean(vals) if vals else None


def stddev(values):
    vals = [v for v in values if v not in ("", None)]
    vals = [float(v) for v in vals]
    if len(vals) < 2:
        return None
    return stdev(vals)


def ci95(values):
    vals = [v for v in values if v not in ("", None)]
    vals = [float(v) for v in vals]
    if len(vals) < 2:
        return None
    sd = stdev(vals)
    return 1.96 * (sd / math.sqrt(len(vals)))


def looks_like_clarification(answer: str) -> bool:
    answer_l = answer.lower()
    cues = ["which paper", "which papers", "do you mean", "which one do you mean"]
    return any(c in answer_l for c in cues)


def looks_like_refusal(answer: str) -> bool:
    answer_l = answer.lower()
    cues = [
        "outside the project",
        "outside the uploaded papers",
        "outside the uploaded sources",
        "outside the project scope",
        "i cannot answer that from the project",
        "i can't answer that from the project",
        "i can't answer that from the uploaded project papers",
        "not supported by the project sources",
    ]
    return any(c in answer_l for c in cues)


def get_behavior_label(row: dict) -> str:
    action = row.get("action")
    if action in {"answer", "clarify", "refuse"}:
        return action

    behavior = row.get("answer_behavior")
    if behavior in {"answer", "clarify", "refuse"}:
        return behavior
    if row.get("insufficient_evidence") is True:
        return "refuse"
    answer = row.get("answer", "")
    if looks_like_clarification(answer):
        return "clarify"
    if looks_like_refusal(answer) or "insufficient evidence" in answer.lower():
        return "refuse"
    return "answer"


def compute_answered_rate(output_rows):
    if not output_rows:
        return None
    count = sum(1 for r in output_rows if get_behavior_label(r) == "answer")
    return count / len(output_rows)


def compute_clarified_rate(output_rows):
    if not output_rows:
        return None
    return sum(1 for r in output_rows if get_behavior_label(r) == "clarify") / len(output_rows)


def compute_refused_rate(output_rows):
    if not output_rows:
        return None
    return sum(1 for r in output_rows if get_behavior_label(r) == "refuse") / len(output_rows)


def compute_over_clarification_rate(output_rows, dataset_rows):
    candidates = [r for r in output_rows if not dataset_rows[r["id"]]["should_clarify"]]
    if not candidates:
        return None
    return sum(1 for r in candidates if get_behavior_label(r) == "clarify") / len(candidates)


def compute_over_refusal_rate(output_rows, dataset_rows):
    candidates = [r for r in output_rows if not dataset_rows[r["id"]]["should_refuse"]]
    if not candidates:
        return None
    return sum(1 for r in candidates if get_behavior_label(r) == "refuse") / len(candidates)


def summarize_system(judged_rows, direct_rows=None, output_rows=None, dataset_rows=None):
    out = {}

    judged_metrics = {
        "correctness": [r["correctness"] for r in judged_rows],
        "completeness": [r["completeness"] for r in judged_rows],
        "relevance": [r["relevance"] for r in judged_rows],
        "helpfulness": [r["helpfulness"] for r in judged_rows],
        "faithfulness": [r["faithfulness"] for r in judged_rows if r["faithfulness"] is not None],
        "followup_success": [r["followup_success"] for r in judged_rows if r.get("followup_success") is not None],
    }

    for metric_name, values in judged_metrics.items():
        out[f"{metric_name}_mean"] = avg(values)
        out[f"{metric_name}_std"] = stddev(values)
        out[f"{metric_name}_ci95"] = ci95(values)

    if direct_rows is not None and judged_rows:
        keys = next(iter(direct_rows.values())).keys()
        for key in keys:
            if key == "id":
                continue
            vals = [direct_rows[r["id"]][key] for r in judged_rows]
            out[f"{key}_mean"] = avg(vals)
            out[f"{key}_std"] = stddev(vals)
            out[f"{key}_ci95"] = ci95(vals)

    if output_rows is not None and dataset_rows is not None:
        out["answered_rate"] = compute_answered_rate(output_rows)
        out["clarified_rate"] = compute_clarified_rate(output_rows)
        out["refused_rate"] = compute_refused_rate(output_rows)
        out["over_clarification_rate"] = compute_over_clarification_rate(output_rows, dataset_rows)
        out["over_refusal_rate"] = compute_over_refusal_rate(output_rows, dataset_rows)

        latencies = [r.get("latency_sec") for r in output_rows if r.get("latency_sec") is not None]
        out["avg_latency_sec"] = avg(latencies)
        out["latency_std"] = stddev(latencies)
        out["latency_ci95"] = ci95(latencies)

        input_tokens = [r.get("input_tokens") for r in output_rows if r.get("input_tokens") is not None]
        output_tokens = [r.get("output_tokens") for r in output_rows if r.get("output_tokens") is not None]
        costs = [r.get("cost_usd") for r in output_rows if r.get("cost_usd") is not None]

        out["avg_input_tokens"] = avg(input_tokens)
        out["avg_output_tokens"] = avg(output_tokens)
        out["avg_cost_usd"] = avg(costs)

    return out


def summarize_pairwise(rows):
    total = len(rows)
    if total == 0:
        return {}
    a_wins = sum(1 for r in rows if r["winner"] == "A")
    b_wins = sum(1 for r in rows if r["winner"] == "B")
    ties = sum(1 for r in rows if r["winner"] == "tie")
    return {
        "a_win_rate": a_wins / total,
        "b_win_rate": b_wins / total,
        "tie_rate": ties / total,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("[evaluation] starting summarize_results")

    dataset_rows = load_dataset_rows()
    categories = load_categories()

    litspace_j = read_jsonl(OUTPUTS_DIR / "judge_litspace.jsonl")
    zero_j = read_jsonl(OUTPUTS_DIR / "judge_zero_shot.jsonl")
    summary_j = read_jsonl(OUTPUTS_DIR / "judge_summary_few_shot.jsonl")

    litspace_o = read_jsonl(OUTPUTS_DIR / "litspace_outputs.jsonl")
    zero_o = read_jsonl(OUTPUTS_DIR / "zero_shot_outputs.jsonl")
    summary_o = read_jsonl(OUTPUTS_DIR / "summary_few_shot_outputs.jsonl")

    litspace_d = load_csv(OUTPUTS_DIR / "direct_metrics_litspace.csv")
    zero_d = load_csv(OUTPUTS_DIR / "direct_metrics_zero_shot.csv")
    summary_d = load_csv(OUTPUTS_DIR / "direct_metrics_summary_few_shot.csv")

    pairwise_zero = read_jsonl(OUTPUTS_DIR / "pairwise_litspace_vs_zero_shot.jsonl")
    pairwise_summary = read_jsonl(OUTPUTS_DIR / "pairwise_litspace_vs_summary_few_shot.jsonl")

    overall = {
        "litspace_rag": summarize_system(litspace_j, litspace_d, litspace_o, dataset_rows),
        "zero_shot": summarize_system(zero_j, zero_d, zero_o, dataset_rows),
        "summary_few_shot": summarize_system(summary_j, summary_d, summary_o, dataset_rows),
    }

    pairwise = {
        "litspace_vs_zero_shot": summarize_pairwise(pairwise_zero),
        "litspace_vs_summary_few_shot": summarize_pairwise(pairwise_summary),
    }

    by_category = {}
    for category in sorted(set(categories.values())):
        lit_rows = [r for r in litspace_j if categories[r["id"]] == category]
        zero_rows = [r for r in zero_j if categories[r["id"]] == category]
        summary_rows = [r for r in summary_j if categories[r["id"]] == category]

        lit_out = [r for r in litspace_o if categories[r["id"]] == category]
        zero_out = [r for r in zero_o if categories[r["id"]] == category]
        summary_out = [r for r in summary_o if categories[r["id"]] == category]

        by_category[category] = {
            "litspace_rag": summarize_system(lit_rows, litspace_d, lit_out, dataset_rows) if lit_rows else {},
            "zero_shot": summarize_system(zero_rows, zero_d, zero_out, dataset_rows) if zero_rows else {},
            "summary_few_shot": summarize_system(summary_rows, summary_d, summary_out, dataset_rows) if summary_rows else {},
        }

    with (RESULTS_DIR / "metrics_summary.json").open("w", encoding="utf-8") as f:
        json.dump({"overall": overall, "pairwise": pairwise, "by_category": by_category}, f, indent=2)

    with (RESULTS_DIR / "metrics_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scope", "group", "system", "metric", "value"])

        for system, metrics in overall.items():
            for metric, value in metrics.items():
                writer.writerow(["overall", "all", system, metric, value])

        for pair_name, metrics in pairwise.items():
            for metric, value in metrics.items():
                writer.writerow(["pairwise", "all", pair_name, metric, value])

        for category, systems in by_category.items():
            for system, metrics in systems.items():
                for metric, value in metrics.items():
                    writer.writerow(["category", category, system, metric, value])

    with (RESULTS_DIR / "error_analysis.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "category", "system_name", "failure_type", "short_reason"])
        for row in litspace_j + zero_j + summary_j:
            if row["failure_type"] != "good":
                writer.writerow([row["id"], categories[row["id"]], row["system_name"], row["failure_type"], row["short_reason"]])

    print(f"[evaluation] wrote {RESULTS_DIR / 'metrics_summary.json'}")
    print(f"[evaluation] wrote {RESULTS_DIR / 'metrics_summary.csv'}")
    print(f"[evaluation] wrote {RESULTS_DIR / 'error_analysis.csv'}")
    print("[evaluation] summarize_results complete")


if __name__ == "__main__":
    main()
