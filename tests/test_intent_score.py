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
        "expected": {"decision": "no_action", "parse_candidates": [{"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "negative", "negated_intents": ["order.cancel"]}], "route_tasks": [], "polarity": "negative", "negated_intents": ["order.cancel"], "references": {}, "missing_slots": [], "ambiguity_type": None},
    }]
    predictions = [{
        "id": "I-22",
        "parsed": {"decision": "no_action", "tasks": [{"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "negative"}], "negated_intents": [], "references": {}},
        "plan": {"decision": "no_action"}, "call": {}, "error": None,
    }]
    result = score(gold, predictions)
    assert result["polarity"]["summary_correct"] == 1
    assert result["polarity"]["candidate_polarity_exact_correct"] == 1
    assert result["polarity"]["summary_accuracy"] == 1.0
    assert result["polarity"]["candidate_exact_accuracy"] == 1.0
    assert result["negated_intents_exact"]["correct"] == 1
    assert result["negated_intents_exact"]["total"] == 1
    assert result["negated_intents_exact"]["exact_given_parse"] == {"correct": 1, "total": 1}


def test_score_checks_candidate_polarity_for_mixed_intents():
    gold = [{
        "id": "I-mixed", "gold_status": "draft", "group": "negation_pair",
        "expected": {
            "decision": "route",
            "parse_candidates": [
                {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "positive", "negated_intents": []},
                {"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "negative", "negated_intents": ["order.cancel"]},
            ],
            "route_tasks": [{"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}}],
            "polarity": "positive", "negated_intents": ["order.cancel"], "references": {}, "missing_slots": [], "ambiguity_type": None,
        },
    }]
    predictions = [{
        "id": "I-mixed",
        "parsed": {"decision": "route", "tasks": [
            {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "positive"},
            {"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}, "polarity": "negative", "negated_intents": ["order.cancel"]},
        ], "negated_intents": ["order.cancel"], "references": {}},
        "plan": {"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001", "source": "current_turn"}}}]},
        "call": {}, "error": None,
    }]
    result = score(gold, predictions)
    assert result["polarity"]["summary_correct"] == 1
    assert result["polarity"]["candidate_polarity_exact_correct"] == 1


def test_score_separates_schema_failures_from_provider_errors():
    gold = [{
        "id": "I-schema", "gold_status": "draft", "group": "schema",
        "expected": {"decision": "clarify", "parse_candidates": [], "route_tasks": [], "polarity": "positive", "negated_intents": [], "references": {}, "missing_slots": [], "ambiguity_type": "empty_parse"},
    }]
    predictions = [
        {"_meta": True, "status": "draft_preview", "benchmark_version": "intent-v1-draft"},
        {"id": "I-schema", "parsed": None, "plan": None, "call": {"model_id": "m", "provider": "gemini", "latency_ms": 100.0, "prompt_tokens": 10, "output_tokens": 5, "retries": 1, "rate_limited": False}, "error": "schema_validation", "error_details": ["json_invalid"]},
    ]
    result = score(gold, predictions)
    assert result["serving"]["provider_errors"] == 0
    assert result["serving"]["schema_failures"] == 1
    assert result["serving"]["api_calls_observed"] == 1
    assert result["serving"]["prompt_tokens_total"] == 10
    assert result["error_taxonomy"] == {"OUTPUT_SCHEMA_FAILURE": 1}
    assert result["availability"] == {"parsed": 0, "planned": 0, "total": 1}
    assert result["route_task_exact"] == {"correct": 0, "total": 1, "exact_given_plan": {"correct": 0, "total": 0}}
    assert result["polarity"]["summary_correct"] == 0
    assert result["references_exact"] == {"correct": 0, "total": 1, "exact_given_plan": {"correct": 0, "total": 0}}
    assert result["ambiguity_type_exact"]["parser_correct"] == 0
    assert result["missing_slots_exact"]["parser_correct"] == 0
    assert result["negated_intents_exact"]["correct"] == 0


def test_score_does_not_label_provider_failures_as_semantic_parse_errors():
    gold = [{
        "id": "I-provider", "gold_status": "draft", "group": "provider",
        "expected": {
            "decision": "route",
            "parse_candidates": [{"intent_id": "order.lookup", "slots": {}}],
            "route_tasks": [{"intent_id": "order.lookup", "slots": {}}],
            "polarity": "positive", "negated_intents": [], "references": {},
            "missing_slots": [], "ambiguity_type": None, "task_outcomes": [],
        },
    }]
    predictions = [
        {"_meta": True, "status": "draft_preview", "benchmark_version": "intent-v1-draft"},
        {"id": "I-provider", "parsed": None, "plan": None, "call": {}, "error": "TransientError"},
    ]
    result = score(gold, predictions)
    assert result["serving"]["provider_errors"] == 1
    assert result["error_taxonomy"] == {"PROVIDER_FAILURE": 1}
    assert result["task_outcome_exact"] == {"correct": 0, "total": 1, "exact_given_plan": {"correct": 0, "total": 0}}


def test_score_contrast_pair_requires_both_outputs_for_conditional_credit():
    gold = [
        {
            "id": "I-pair-positive", "pair_with": "I-pair-negative", "gold_status": "draft", "group": "negation_pair",
            "expected": {
                "decision": "route", "parse_candidates": [{"intent_id": "order.lookup", "slots": {}, "polarity": "positive"}],
                "route_tasks": [{"intent_id": "order.lookup", "slots": {}}], "polarity": "positive", "negated_intents": [],
                "references": {}, "missing_slots": [], "ambiguity_type": None,
            },
        },
        {
            "id": "I-pair-negative", "pair_with": "I-pair-positive", "gold_status": "draft", "group": "negation_pair",
            "expected": {
                "decision": "no_action", "parse_candidates": [{"intent_id": "order.lookup", "slots": {}, "polarity": "negative", "negated_intents": ["order.lookup"]}],
                "route_tasks": [], "polarity": "negative", "negated_intents": ["order.lookup"],
                "references": {}, "missing_slots": [], "ambiguity_type": None,
            },
        },
    ]
    predictions = [
        {"id": "I-pair-positive", "parsed": {"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {}, "polarity": "positive"}], "negated_intents": [], "references": {}}, "plan": {"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {}}]}, "call": {}, "error": None},
        {"id": "I-pair-negative", "parsed": None, "plan": None, "call": {}, "error": "TransientError"},
    ]
    result = score(gold, predictions)
    assert result["contrast_pairs"] == {"both_cases_correct": 0, "total_pairs": 1, "both_cases_correct_given_outputs": {"correct": 0, "total": 0}}


def test_score_does_not_label_missing_plan_as_reference_error():
    gold = [{
        "id": "I-plan-error", "gold_status": "draft", "group": "reference",
        "expected": {
            "decision": "route", "parse_candidates": [{"intent_id": "order.lookup", "slots": {}}],
            "route_tasks": [{"intent_id": "order.lookup", "slots": {}}], "polarity": "positive",
            "negated_intents": [], "references": {"order_id": "BM-1001"}, "missing_slots": [], "ambiguity_type": None,
        },
    }]
    predictions = [
        {"_meta": True, "status": "draft_preview", "benchmark_version": "intent-v1-draft"},
        {"id": "I-plan-error", "parsed": {"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {}}]}, "plan": None, "call": {}, "error": "PlannerError"},
    ]
    result = score(gold, predictions)
    assert result["error_taxonomy"] == {"PROVIDER_FAILURE": 1}
