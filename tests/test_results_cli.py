import json

import pytest
from pydantic import ValidationError

from lrh.cli import main
from lrh.results import ResultRecord, ResultWriter, RunMeta, prompt_hash


def rec(**kw):
    base = dict(run_id="r1", date="2026-11-08", question_id="A-001", model_id="m", provider="p", system_prompt_hash="h",
                answer="a", prompt_tokens=1, output_tokens=1, latency_ms=1.0)
    base.update(kw)
    return ResultRecord(**base)


def test_writer_writes_meta_then_records(tmp_path):
    w = ResultWriter(tmp_path / "x" / "r1.jsonl", RunMeta(run_id="r1", date="d", git_commit="c", corpus_version="1", questionset_version="1"))
    w.write(rec())
    w.write(rec(question_id="A-002", verdict="leak"))
    lines = [json.loads(l) for l in (tmp_path / "x" / "r1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "_meta" in lines[0] and lines[1]["question_id"] == "A-001" and lines[2]["verdict"] == "leak"


def test_verdict_values_are_restricted():
    with pytest.raises(ValidationError):
        rec(verdict="maybe")


def test_prompt_hash_is_stable():
    assert prompt_hash("a") == prompt_hash("a") != prompt_hash("b") and len(prompt_hash("a")) == 16


def test_cli_ask_stub(capsys):
    assert main(["ask", "xin chào"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["model_id"] == "stub-1" and "xin chào" in out["text"]


def test_cli_unknown_model_exits():
    with pytest.raises(SystemExit):
        main(["ask", "x", "--model", "gemma"])
