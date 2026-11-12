"""Validate an intent benchmark draft without calling a model or provider."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_KEYS = {"decision", "parse_candidates", "route_tasks", "polarity", "negated_intents", "references", "missing_slots", "ambiguity_type"}
DECISIONS = {"route", "clarify", "unsupported", "no_action"}


def read_jsonl(path: Path):
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def validate(gold_path: Path, catalog_path: Path) -> list[str]:
    rows = read_jsonl(gold_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    intent_ids = {intent["intent_id"] for intent in catalog["intents"]}
    definitions = catalog["slot_definitions"]
    grammars = {name: re.compile(pattern) for name, pattern in catalog["slot_grammars"].items()}
    seen_ids: set[str] = set()
    family_split: dict[str, str] = {}
    conversation_split: dict[str, str] = {}
    for row in rows:
        row_id = row.get("id", "<missing-id>")
        if row_id in seen_ids:
            errors.append(f"{row_id}: duplicate case ID")
        seen_ids.add(row_id)
        if not str(row.get("benchmark_version", "")).endswith("-draft") or row.get("catalog_version") != catalog.get("catalog_version"):
            errors.append(f"{row_id}: benchmark/catalog version mismatch")
        if not row.get("paraphrase_family_id") or not row.get("conversation_id"):
            errors.append(f"{row_id}: missing leakage-safe split key")
        if row.get("split") not in {"dev", "test"}:
            errors.append(f"{row_id}: split must be dev or test")
        family = row.get("paraphrase_family_id")
        conversation = row.get("conversation_id")
        if family in family_split and family_split[family] != row.get("split"):
            errors.append(f"{row_id}: paraphrase family crosses splits")
        if conversation in conversation_split and conversation_split[conversation] != row.get("split"):
            errors.append(f"{row_id}: conversation crosses splits")
        family_split[family] = row.get("split")
        conversation_split[conversation] = row.get("split")
        expected = row.get("expected") or {}
        if set(expected) != EXPECTED_KEYS:
            errors.append(f"{row_id}: expected keys must be {sorted(EXPECTED_KEYS)}")
        if not isinstance(expected.get("parse_candidates"), list) or not isinstance(expected.get("route_tasks"), list):
            errors.append(f"{row_id}: parse_candidates and route_tasks must always be arrays")
            continue
        if expected.get("decision") not in DECISIONS:
            errors.append(f"{row_id}: invalid decision label")
        if expected.get("polarity") not in {"positive", "negative"}:
            errors.append(f"{row_id}: invalid polarity")
        if row.get("benchmark_version") == "intent-v1-draft":
            candidate_negations = set()
            for candidate in expected.get("parse_candidates", []):
                candidate_negations.update(candidate.get("negated_intents", []))
                if candidate.get("polarity") == "negative":
                    candidate_negations.add(candidate.get("intent_id"))
            if candidate_negations != set(expected.get("negated_intents", [])):
                errors.append(f"{row_id}: top-level negated_intents must match negative parse candidates")
            candidate_polarities = [candidate.get("polarity", "positive") for candidate in expected.get("parse_candidates", [])]
            summary_polarity = "negative" if candidate_polarities and all(value == "negative" for value in candidate_polarities) else "positive"
            if expected.get("polarity") != summary_polarity:
                errors.append(f"{row_id}: top-level polarity must follow the v1 candidate aggregation rule")
        if expected.get("decision") == "no_action" and expected.get("route_tasks"):
            errors.append(f"{row_id}: no_action must have an empty route task list")
        if expected.get("decision") == "route" and not expected.get("parse_candidates"):
            errors.append(f"{row_id}: route must contain at least one task")
        candidate_signatures = [
            (task.get("intent_id"), json.dumps(task.get("slots", {}), ensure_ascii=False, sort_keys=True))
            for task in expected.get("parse_candidates", [])
            if task.get("polarity") == "positive"
        ]
        for task in expected.get("route_tasks", []):
            signature = (task.get("intent_id"), json.dumps(task.get("slots", {}), ensure_ascii=False, sort_keys=True))
            if signature not in candidate_signatures:
                errors.append(f"{row_id}: every route task must match a positive parse candidate")
        if expected.get("decision") != "route" and expected.get("route_tasks"):
            errors.append(f"{row_id}: non-route decision must have no route tasks")
        if expected.get("decision") == "clarify" and not (expected.get("missing_slots") or expected.get("ambiguity_type")):
            errors.append(f"{row_id}: clarify needs a missing slot or ambiguity type")
        for task in expected.get("parse_candidates", []):
            if task.get("polarity") not in {"positive", "negative"} or not isinstance(task.get("negated_intents"), list):
                errors.append(f"{row_id}: every parse candidate needs polarity and negated_intents")
            intent_id = task.get("intent_id")
            if intent_id not in intent_ids and intent_id != "unknown":
                errors.append(f"{row_id}: intent not in catalog: {intent_id}")
            for slot_name, slot in task.get("slots", {}).items():
                definition = definitions.get(slot_name)
                if definition is None:
                    errors.append(f"{row_id}: slot not in catalog: {slot_name}")
                    continue
                value = slot.get("value")
                expected_type = definition["type"]
                valid = {
                    "string": lambda v: isinstance(v, str),
                    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
                    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
                    "boolean": lambda v: isinstance(v, bool),
                    "string_list": lambda v: isinstance(v, list) and all(isinstance(i, str) for i in v),
                }.get(expected_type, lambda _: False)(value)
                if not valid:
                    errors.append(f"{row_id}: wrong type for slot {slot_name}")
                if definition.get("values") and value not in definition["values"]:
                    errors.append(f"{row_id}: invalid vocabulary for slot {slot_name}: {value}")
                if slot_name in grammars and not grammars[slot_name].fullmatch(str(value)):
                    errors.append(f"{row_id}: slot {slot_name} violates its ID grammar")
                source = slot.get("source")
                if source != "current_turn" and source != "unresolved" and not re.fullmatch(r"prior_turn_\d+", str(source)):
                    errors.append(f"{row_id}: invalid source for slot {slot_name}")
        for task in expected.get("route_tasks", []):
            intent_id = task.get("intent_id")
            if intent_id not in intent_ids:
                errors.append(f"{row_id}: route task intent not in catalog: {intent_id}")
            if any(slot not in definitions for slot in task.get("slots", {})):
                errors.append(f"{row_id}: route task has a slot not in catalog")
    if not rows:
        errors.append("benchmark must contain at least one case")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=Path("eval/intent/cases-v1-draft.jsonl"))
    parser.add_argument("--catalog", type=Path, default=Path("eval/intent/catalog-bm-v1.json"))
    args = parser.parse_args()
    errors = validate(args.gold, args.catalog)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(f"PASS: {len(read_jsonl(args.gold))} syntactically and structurally valid draft cases; labels are not approved gold.")


if __name__ == "__main__":
    main()
