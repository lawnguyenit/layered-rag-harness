"""CLI giai đoạn 0. `--model stub` (mặc định, không tốn lượt) hoặc ID mô hình trong limits_table.py (ví dụ gemma-4-31b-it)."""
from __future__ import annotations

import argparse
import json

from lrh.config import ConfigError, load_settings
from lrh.contracts import AdapterError, GenerateRequest, Message
from lrh.factory import build_generator


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lrh")
    sub = p.add_subparsers(dest="cmd", required=True)
    ask = sub.add_parser("ask", help="hỏi mô hình một câu")
    ask.add_argument("question")
    ask.add_argument("--model", default="stub")
    ask.add_argument("--system", default="")
    ask.add_argument("--no-cache", action="store_true")
    args = p.parse_args(argv)
    try:
        model = build_generator(args.model, load_settings(), use_cache=not args.no_cache)
        msgs = ([Message(role="system", content=args.system)] if args.system else []) + [Message(role="user", content=args.question)]
        out = model.generate(GenerateRequest(messages=msgs))
    except (ConfigError, AdapterError) as e:
        raise SystemExit(f"Lỗi: {type(e).__name__}: {e}")
    print(json.dumps(out.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0
