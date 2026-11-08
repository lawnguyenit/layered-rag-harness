"""CLI giai đoạn 0. Hiện chỉ có adapter giả; adapter Gemini thật ở bước 0.5."""
from __future__ import annotations

import argparse
import json

from lrh.adapters.stub import StubModel
from lrh.contracts import GenerateRequest, Message


def build_model(name: str):
    if name == "stub":
        return StubModel()
    raise SystemExit(f"Chưa có adapter '{name}' (bước 0.5). Dùng --model stub.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lrh")
    sub = p.add_subparsers(dest="cmd", required=True)
    ask = sub.add_parser("ask", help="hỏi mô hình một câu")
    ask.add_argument("question")
    ask.add_argument("--model", default="stub")
    ask.add_argument("--system", default="")
    args = p.parse_args(argv)
    model = build_model(args.model)
    msgs = ([Message(role="system", content=args.system)] if args.system else []) + [Message(role="user", content=args.question)]
    out = model.generate(GenerateRequest(messages=msgs))
    print(json.dumps(out.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0
