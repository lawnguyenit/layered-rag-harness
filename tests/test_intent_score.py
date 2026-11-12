import pytest

from eval.intent.score import score


def test_score_reports_false_dispatch_beside_coverage_and_marks_draft_preview():
    gold = [
        {
            "id": "I-1",
            "gold_status": "draft",
            "group": "reference",
            "expected": {
                "decision": "clarify",
                "parse_candidates": [{"intent_id": "order.lookup", "slots": {}}],
                "route_tasks": [],
                "polarity": "positive",
                "negated_intents": [],
                "references": {},
                "missing_slots": ["order_id"],
                "ambiguity_type": "unresolved_reference",
            },
        }
    ]
    predictions = [
        {"_meta": True, "status": "draft_preview", "benchmark_version": "intent-v0-draft"},
        {
            "id": "I-1",
            "parsed": {"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}}], "negated_intents": [], "references": {}},
            "plan": {"decision": "route"},
            "call": {},
            "error": None,
        },
    ]
    result = score(gold, predictions)
    assert result["score_status"] == "draft_preview_not_reportable_as_accuracy"
    assert result["uncertainty"]["false_dispatch"] == 1
    coverage = result["uncertainty"]["coverage"]
    assert (coverage["routed"], coverage["total"], coverage["rate"]) == (1, 1, 1.0)
    assert 0.20 < coverage["wilson_95"]["low"] < 0.21
    assert coverage["wilson_95"]["high"] == 1.0
    assert result["decision"]["confusion"]["clarify"]["route"] == 1


def test_score_counts_pure_negation_as_negative_no_action():
    gold = [{
        "id": "I-22", "gold_status": "draft", "group": "negation",
        "expected": {"decision": "no_action", "parse_candidates": [{"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}}], "route_tasks": [], "polarity": "negative", "negated_intents": [], "references": {}, "missing_slots": [], "ambiguity_type": None},
    }]
    predictions = [{
        "id": "I-22",
        "parsed": {"decision": "no_action", "tasks": [{"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "negative"}], "negated_intents": [], "references": {}},
        "plan": {"decision": "no_action"}, "call": {}, "error": None,
    }]
    result = score(gold, predictions)
    assert result["polarity"] == {"correct": 1, "total": 1, "accuracy": 1.0}
    assert result["negated_intents_exact"] == {"correct": 1, "total": 1}
