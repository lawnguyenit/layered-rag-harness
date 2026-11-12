"""Run the 5a draft suite once and store raw parse/plan outputs for scoring."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from lrh.config import load_settings
from lrh.factory import build_generator
from lrh.request_contracts import Actor
from lrh.routing import ModelIntentParser, RouteCatalog, RoutePlanner


def _jsonl(path: Path):
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--gold", type=Path, default=Path("eval/intent/cases-v1-draft.jsonl"))
    cli.add_argument("--catalog", type=Path, default=Path("eval/intent/catalog-bm-v1.json"))
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--model-id", default=None)
    cli.add_argument("--limit", type=int, default=None, help="Run the first N cases for a pilot only")
    cli.add_argument("--split", choices=("all", "dev", "test"), default="all")
    args = cli.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite existing result: {args.out}")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")

    catalog = RouteCatalog.load(args.catalog)
    cases = list(_jsonl(args.gold))
    if args.split != "all":
        cases = [row for row in cases if row.get("split") == args.split]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No evaluation cases found")

    settings = load_settings()
    model_id = args.model_id or settings.model_id
    model = build_generator(model_id, settings, use_cache=False)
    parser = ModelIntentParser(model, catalog)
    planner = RoutePlanner(catalog)
    gold_hash = hashlib.sha256(args.gold.read_bytes()).hexdigest()
    metadata = {
        "_meta": True,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "benchmark_version": cases[0].get("benchmark_version", "unknown"),
        "catalog_version": catalog.catalog_version,
        "gold_sha256": gold_hash,
        "prompt_sha256": parser.prompt_hash,
        "model_id": model_id,
        "provider": getattr(model, "provider", "unknown"),
        "limit": args.limit,
        "split": args.split,
        "status": "draft_preview" if any(row.get("gold_status") != "approved" for row in cases) else "frozen_candidate",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for case in cases:
            case_id = case["id"]
            try:
                started = time.perf_counter()
                parsed, call = parser.parse_with_metadata(case["utterance"], case.get("context", []))
                parse_latency_ms = (time.perf_counter() - started) * 1000
                plan = planner.plan(
                    parsed,
                    question=case["utterance"],
                    history=case.get("context", []),
                    actor=Actor(subject="evaluation-only", role="visitor"),
                    request_id=case_id,
                    conversation_id=case.get("conversation_id", case_id),
                )
                result = {
                    "id": case_id,
                    "parsed": parsed.model_dump(mode="json"),
                    "plan": plan.model_dump(mode="json"),
                    "call": call.__dict__,
                    "parse_latency_ms": parse_latency_ms,
                    "error": None,
                }
            except Exception as exc:
                result = {"id": case_id, "parsed": None, "plan": None, "call": None, "error": type(exc).__name__}
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()


if __name__ == "__main__":
    main()
