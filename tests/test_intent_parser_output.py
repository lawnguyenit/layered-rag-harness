from __future__ import annotations

import pytest

from lrh.contracts import GenerateResult, Usage
from lrh.routing import IntentOutputError, ModelIntentParser, RouteCatalog


class FakeModel:
    provider = "fake"
    model_id = "fake-parser"

    def __init__(self, text: str):
        self.text = text
        self.request = None

    def generate(self, request):
        self.request = request
        return GenerateResult(
            text=self.text,
            usage=Usage(prompt_tokens=17, output_tokens=8),
            model_id=self.model_id,
            provider=self.provider,
            latency_ms=12.5,
        )


def catalog() -> RouteCatalog:
    return RouteCatalog.model_validate(
        {
            "catalog_version": "test-v1",
            "slot_definitions": {"order_id": {"type": "string"}},
            "slot_grammars": {"order_id": r"^BM-[0-9]{4}$"},
            "intents": [
                {"intent_id": "order.lookup", "required_slots": ["order_id"], "entity_slots": ["order_id"]}
            ],
        }
    )


def test_parser_requests_json_and_parses_valid_output():
    model = FakeModel('{"decision":"route","tasks":[{"intent_id":"order.lookup","slots":{"order_id":{"value":"BM-1001","source":"current_turn"}}}]}')
    parser = ModelIntentParser(model, catalog())
    result, metadata = parser.parse_with_metadata("BM-1001 giao chưa?", [])
    assert result.decision == "route"
    assert model.request.response_mime_type == "application/json"
    assert metadata.prompt_tokens == 17


def test_parser_keeps_safe_call_metadata_when_json_is_invalid():
    model = FakeModel("not-json")
    parser = ModelIntentParser(model, catalog())
    with pytest.raises(IntentOutputError) as captured:
        parser.parse_with_metadata("BM-1001 giao chưa?", [])
    assert captured.value.metadata.model_id == "fake-parser"
    assert captured.value.metadata.prompt_tokens == 17
    assert captured.value.issue_types == ["json_invalid"]
    assert "not-json" not in str(captured.value)
