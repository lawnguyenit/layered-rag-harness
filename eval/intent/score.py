"""Score raw 5a parse/plan JSONL outputs; draft labels are always marked preview-only."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DECISIONS = ("route", "clarify", "unsupported", "no_action")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def gold_candidates(expected: dict[str, Any]) -> list[dict[str, Any]]:
    return expected.get("parse_candidates", [])


def gold_route_tasks(expected: dict[str, Any]) -> list[dict[str, Any]]:
    return expected.get("route_tasks", [])


def pred_tasks(parsed: dict[str, Any] | None) -> list[dict[str, Any]]:
    return (parsed or {}).get("tasks", [])


def intent_counts(tasks: list[dict[str, Any]]) -> Counter[str]:
    return Counter(task.get("intent_id", "") for task in tasks)


def slot_counts(tasks: list[dict[str, Any]]) -> Counter[tuple[str, str, str]]:
    return Counter(
        (task.get("intent_id", ""), name, canonical(slot.get("value")))
        for task in tasks
        for name, slot in task.get("slots", {}).items()
    )


def slot_provenance_counts(tasks: list[dict[str, Any]]) -> Counter[tuple[str, str, str, str]]:
    return Counter(
        (task.get("intent_id", ""), name, canonical(slot.get("value")), slot.get("source", "current_turn"))
        for task in tasks
        for name, slot in task.get("slots", {}).items()
    )


def string_keys(counts: Counter) -> Counter[str]:
    return Counter({canonical(key): value for key, value in counts.items()})


def task_signature(task: dict[str, Any]) -> str:
    slots = {name: slot.get("value") for name, slot in task.get("slots", {}).items()}
    return canonical({"intent_id": task.get("intent_id"), "slots": slots})


def task_multiset(tasks: list[dict[str, Any]]) -> Counter[str]:
    return Counter(task_signature(task) for task in tasks)


def macro_f1(gold: Counter[str], pred: Counter[str]) -> dict[str, Any]:
    labels = sorted(set(gold) | set(pred))
    per_label = {}
    scores = []
    for label in labels:
        tp = min(gold[label], pred[label])
        fp = pred[label] - tp
        fn = gold[label] - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}
        scores.append(f1)
    tp_total = sum(min(gold[label], pred[label]) for label in labels)
    fp_total = sum(pred[label] - min(gold[label], pred[label]) for label in labels)
    fn_total = sum(gold[label] - min(gold[label], pred[label]) for label in labels)
    precision = tp_total / (tp_total + fp_total) if tp_total + fp_total else 0.0
    recall = tp_total / (tp_total + fn_total) if tp_total + fn_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"micro": {"tp": tp_total, "fp": fp_total, "fn": fn_total, "precision": precision, "recall": recall, "f1": f1}, "macro_f1": sum(scores) / len(scores) if scores else 0.0, "per_intent": per_label}


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    index = max(0, math.ceil(pct * len(values)) - 1)
    return values[index]


def wilson(success: int, total: int) -> dict[str, float | None]:
    if total <= 0:
        return {"low": None, "high": None}
    z = 1.96
    p = success / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return {"low": max(0.0, center - margin), "high": min(1.0, center + margin)}


def score(gold_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]], split: str = "all") -> dict[str, Any]:
    metadata = next((row for row in prediction_rows if row.get("_meta")), {})
    predictions = {row["id"]: row for row in prediction_rows if not row.get("_meta")}
    if split != "all":
        gold_rows = [row for row in gold_rows if row.get("split") == split]
    eligible = [row for row in gold_rows if row.get("gold_status") == "approved"]
    draft_preview = len(eligible) != len(gold_rows) or metadata.get("status") == "draft_preview"
    rows = eligible if eligible else gold_rows
    count = len(rows)
    decision_confusion = {expected: {actual: 0 for actual in (*DECISIONS, "provider_error")} for expected in DECISIONS}
    gold_intents: Counter[str] = Counter()
    predicted_intents: Counter[str] = Counter()
    gold_slots: Counter[tuple[str, str, str]] = Counter()
    predicted_slots: Counter[tuple[str, str, str]] = Counter()
    gold_provenance: Counter[tuple[str, str, str, str]] = Counter()
    predicted_provenance: Counter[tuple[str, str, str, str]] = Counter()
    intent_exact = slot_exact = route_task_exact = polarity_correct = negation_exact = reference_exact = 0
    ambiguity_exact = plan_ambiguity_exact = missing_slots_exact = plan_missing_slots_exact = 0
    decision_correct = false_dispatch = wrong_dispatch = clarify_tp = clarify_total = false_clarify = 0
    routed = provider_errors = 0
    errors = []
    latency, model_latency, prompt_tokens, output_tokens, retries, rate_limited, api_calls_observed = [], [], 0, 0, 0, 0, 0
    error_counts: Counter[str] = Counter()
    taxonomy_counts: Counter[str] = Counter()
    group_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"cases": 0, "decision_correct": 0, "routed": 0, "false_dispatch": 0})
    reference_groups: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for gold in rows:
        expected = gold["expected"]
        pred = predictions.get(gold["id"], {})
        parsed = pred.get("parsed")
        plan = pred.get("plan")
        parse_tasks = pred_tasks(parsed)
        expected_candidates = gold_candidates(expected)
        expected_route = gold_route_tasks(expected)
        actual_route = (plan or {}).get("tasks", [])
        gold_intents.update(intent_counts(expected_candidates))
        predicted_intents.update(intent_counts(parse_tasks))
        gold_slots.update(slot_counts(expected_candidates))
        predicted_slots.update(slot_counts(parse_tasks))
        gold_provenance.update(slot_provenance_counts(expected_candidates))
        predicted_provenance.update(slot_provenance_counts(parse_tasks))
        intents_ok = intent_counts(expected_candidates) == intent_counts(parse_tasks)
        slots_ok = task_multiset(expected_candidates) == task_multiset(parse_tasks)
        route_tasks_ok = task_multiset(expected_route) == task_multiset(actual_route)
        intent_exact += int(intents_ok)
        slot_exact += int(slots_ok)
        route_task_exact += int(route_tasks_ok)
        actual_polarity = "negative" if parsed and (parsed.get("decision") == "no_action" or (parsed.get("tasks") and all(t.get("polarity") == "negative" for t in parsed["tasks"]))) else "positive"
        polarity_correct += int(actual_polarity == expected.get("polarity", "positive"))
        actual_negated = set((parsed or {}).get("negated_intents", []))
        for task in parse_tasks:
            actual_negated.update(task.get("negated_intents", []))
            if task.get("polarity") == "negative":
                actual_negated.add(task.get("intent_id"))
        expected_negated = set(expected.get("negated_intents", []))
        if expected.get("polarity") == "negative":
            expected_negated.update(task.get("intent_id") for task in expected_candidates)
        negation_exact += int(actual_negated == expected_negated)
        references_ok = (parsed or {}).get("references", {}) == expected.get("references", {})
        reference_exact += int(references_ok)
        ambiguity_exact += int((parsed or {}).get("ambiguity_type") == expected.get("ambiguity_type"))
        plan_ambiguity_exact += int((plan or {}).get("ambiguity_type") == expected.get("ambiguity_type"))
        missing_slots_exact += int(sorted((parsed or {}).get("missing_slots", [])) == sorted(expected.get("missing_slots", [])))
        plan_missing_slots_exact += int(sorted((plan or {}).get("missing_slots", [])) == sorted(expected.get("missing_slots", [])))
        if "reference" in gold.get("group", ""):
            reference_groups[gold["group"]]["total"] += 1
            reference_groups[gold["group"]]["correct"] += int((parsed or {}).get("references", {}) == expected.get("references", {}))

        actual_decision = plan.get("decision") if plan else "provider_error"
        expected_decision = expected["decision"]
        group = gold.get("group", "unassigned")
        group_counts[group]["cases"] += 1
        group_counts[group]["decision_correct"] += int(actual_decision == expected_decision)
        group_counts[group]["routed"] += int(actual_decision == "route")
        group_counts[group]["false_dispatch"] += int(expected_decision != "route" and actual_decision == "route")
        if expected_decision in decision_confusion:
            decision_confusion[expected_decision][actual_decision] = decision_confusion[expected_decision].get(actual_decision, 0) + 1
        decision_correct += int(actual_decision == expected_decision)
        routed += int(actual_decision == "route")
        provider_errors += int(actual_decision == "provider_error")
        false_dispatch += int(expected_decision != "route" and actual_decision == "route")
        if expected_decision == "route":
            wrong_dispatch += int(actual_decision == "route" and not route_tasks_ok)
            false_clarify += int(actual_decision == "clarify")
        if expected_decision == "clarify":
            clarify_total += 1
            clarify_tp += int(actual_decision == "clarify")

        call = pred.get("call") or {}
        if isinstance(call.get("latency_ms"), (int, float)):
            model_latency.append(float(call["latency_ms"]))
            api_calls_observed += 1
        prompt_tokens += int(call.get("prompt_tokens", 0) or 0)
        output_tokens += int(call.get("output_tokens", 0) or 0)
        retries += int(call.get("retries", 0) or 0)
        rate_limited += int(bool(call.get("rate_limited", False)))
        if isinstance(pred.get("parse_latency_ms"), (int, float)):
            latency.append(float(pred["parse_latency_ms"]))
        if pred.get("error"):
            error_counts[str(pred["error"])] += 1
        categories = []
        if actual_decision == "route" and expected_decision == "clarify":
            categories.append("SHOULD_CLARIFY_BUT_DISPATCHED")
        elif actual_decision == "route" and expected_decision == "unsupported":
            categories.append("UNSUPPORTED_MAPPED_TO_ROUTE")
        elif actual_decision == "route" and expected_decision == "no_action":
            categories.append("NEGATION_SCOPE")
        elif actual_decision == "clarify" and expected_decision == "route":
            categories.append("CLEAR_BUT_OVER_CLARIFIED")
        if not intents_ok:
            categories.append("WRONG_INTENT")
        if not slots_ok:
            categories.append("WRONG_SLOT")
        if actual_polarity != expected.get("polarity", "positive") or actual_negated != expected_negated:
            categories.append("NEGATION_SCOPE")
        if not references_ok:
            categories.append("REFERENCE_RESOLUTION")
        if expected_decision == "route" and actual_decision == "route" and not route_tasks_ok:
            categories.append("MULTI_TASK_DROPPED_OR_MERGED" if len(expected_route) != len(actual_route) else "WRONG_SLOT")
        if pred.get("error"):
            categories.append("OUTPUT_SCHEMA_FAILURE" if pred["error"] in {"ValidationError", "JSONDecodeError"} else "PROVIDER_FAILURE")
        categories = list(dict.fromkeys(categories))
        taxonomy_counts.update(categories)
        if categories:
            errors.append({"id": gold["id"], "expected_decision": expected_decision, "actual_decision": actual_decision, "intent_exact": intents_ok, "parse_slots_exact": slots_ok, "route_tasks_exact": route_tasks_ok, "error_categories": categories, "error": pred.get("error")})

    return {
        "score_status": "draft_preview_not_reportable_as_accuracy" if draft_preview else "approved_labels",
        "benchmark_version": metadata.get("benchmark_version"),
        "catalog_version": metadata.get("catalog_version"),
        "split": split,
        "model_id": metadata.get("model_id"),
        "prompt_sha256": metadata.get("prompt_sha256"),
        "gold_sha256": metadata.get("gold_sha256"),
        "cases": count,
        "decision": {"correct": decision_correct, "total": count, "accuracy": decision_correct / count if count else None, "wilson_95": wilson(decision_correct, count), "confusion": decision_confusion},
        "intent": {"exact_correct": intent_exact, "total": count, "task_micro_macro": macro_f1(gold_intents, predicted_intents)},
        "slots": {"parse_candidate_exact_correct": slot_exact, "total": count, "value_micro_macro": macro_f1(string_keys(gold_slots), string_keys(predicted_slots)), "provenance_exact_correct": sum((gold_provenance & predicted_provenance).values()), "provenance_total": sum(gold_provenance.values())},
        "route_task_exact": {"correct": route_task_exact, "total": count},
        "polarity": {"correct": polarity_correct, "total": count, "accuracy": polarity_correct / count if count else None},
        "negated_intents_exact": {"correct": negation_exact, "total": count},
        "references_exact": {"correct": reference_exact, "total": count},
        "ambiguity_type_exact": {"parser_correct": ambiguity_exact, "plan_correct": plan_ambiguity_exact, "total": count},
        "missing_slots_exact": {"parser_correct": missing_slots_exact, "plan_correct": plan_missing_slots_exact, "total": count},
        "reference_by_group": {group: {**values, "accuracy": values["correct"] / values["total"] if values["total"] else None} for group, values in sorted(reference_groups.items())},
        "contrast_pairs": _score_pairs(rows, predictions),
        "uncertainty": {
            "false_dispatch": false_dispatch,
            "false_dispatch_wilson_95": wilson(false_dispatch, count),
            "clarify_recall": {"correct": clarify_tp, "total": clarify_total, "rate": clarify_tp / clarify_total if clarify_total else None, "wilson_95": wilson(clarify_tp, clarify_total)},
            "false_clarify": false_clarify,
            "coverage": {"routed": routed, "total": count, "rate": routed / count if count else None, "wilson_95": wilson(routed, count)},
            "wrong_dispatch": wrong_dispatch,
        },
        "serving": {"provider_errors": provider_errors, "error_types": dict(error_counts), "timeouts": sum(count for name, count in error_counts.items() if "timeout" in name.casefold()), "schema_failures": sum(count for name, count in error_counts.items() if name in {"ValidationError", "JSONDecodeError"}), "api_calls_observed": api_calls_observed, "model_latency_ms_p50": percentile(model_latency, .50), "model_latency_ms_p95": percentile(model_latency, .95), "parse_latency_ms_p50": percentile(latency, .50), "parse_latency_ms_p95": percentile(latency, .95), "prompt_tokens_total": prompt_tokens, "output_tokens_total": output_tokens, "retries_total": retries, "rate_limited_requests": rate_limited},
        "by_group": {group: {**values, "decision_accuracy": values["decision_correct"] / values["cases"] if values["cases"] else None} for group, values in sorted(group_counts.items())},
        "errors": errors,
        "error_taxonomy": dict(taxonomy_counts),
    }


def _score_pairs(gold_rows: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    indexed = {row["id"]: row for row in gold_rows}
    pairs = set()
    for row in gold_rows:
        other = row.get("pair_with")
        if other in indexed:
            pairs.add(tuple(sorted((row["id"], other))))
    correct = 0
    for first, second in pairs:
        pair_correct = True
        for case_id in (first, second):
            expected = indexed[case_id]["expected"]
            pred = predictions.get(case_id, {})
            parsed = pred.get("parsed") or {}
            plan = pred.get("plan") or {}
            predicted_polarity = "negative" if parsed.get("decision") == "no_action" or (parsed.get("tasks") and all(task.get("polarity") == "negative" for task in parsed["tasks"])) else "positive"
            if plan.get("decision") != expected["decision"] or predicted_polarity != expected["polarity"]:
                pair_correct = False
        correct += int(pair_correct)
    return {"both_cases_correct": correct, "total_pairs": len(pairs)}


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--gold", type=Path, default=Path("eval/intent/cases-v0-draft.jsonl"))
    cli.add_argument("--predictions", type=Path, required=True)
    cli.add_argument("--out", type=Path, default=None)
    cli.add_argument("--split", choices=("all", "dev", "test"), default="all")
    args = cli.parse_args()
    report = score(load_jsonl(args.gold), load_jsonl(args.predictions), split=args.split)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
