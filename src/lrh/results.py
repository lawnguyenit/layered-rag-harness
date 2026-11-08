"""Bản ghi kết quả đo theo docs/DATA-CONTRACT.md mục 7."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class RunMeta(BaseModel):
    run_id: str
    date: str
    git_commit: str
    corpus_version: str
    questionset_version: str


class ResultRecord(BaseModel):
    run_id: str
    date: str
    question_id: str
    model_id: str
    provider: str
    system_prompt_hash: str
    answer: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: float
    retries: int = 0
    rate_limited: bool = False
    cache_hit: bool = False
    grader: Literal["rule", "hand"] = "rule"
    verdict: Literal["pass", "fail", "leak", "false_refusal", "na"] = "na"
    notes: Optional[str] = None


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class ResultWriter:
    def __init__(self, path: Path, meta: RunMeta):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"_meta": meta.model_dump()}, ensure_ascii=False) + "\n")

    def write(self, rec: ResultRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
