"""Thăm dò trước điểm gốc: suy nghĩ (thinking) của mô hình ảnh hưởng độ trễ và hạn max_output_tokens thế nào.
Gọi thẳng SDK (không qua cache/throttle) để thấy phản hồi thô. Khoảng 21 lượt sinh.

    uv run python eval/probe_thinking.py [--model gemma-4-31b-it] [--reps 2]
Ghi eval/results/thinking-probe-<model>-<ngày>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from google.genai import errors, types  # noqa: E402

from lrh.adapters.gemini import _make_client  # noqa: E402
from lrh.config import load_settings  # noqa: E402
from token_profile import split_frontmatter  # noqa: E402

SHORT = "Trả lời đúng một từ: xin chào bằng tiếng Anh?"  # giống tests/test_live.py


def rag_like_prompt() -> str:
    _, body = split_frontmatter((ROOT / "data" / "corpus" / "pub-return-policy.md").read_text(encoding="utf-8"))
    q = "Mình cần báo món hư hỏng trong bao lâu sau khi nhận hàng?"  # A-001
    return f"Chỉ dựa vào tài liệu sau để trả lời ngắn gọn.\n\n<tài liệu>\n{body}\n</tài liệu>\n\nCâu hỏi: {q}"


CONFIGS: dict[str, dict] = {
    "default": {},
    "level=minimal": {"thinking_level": "MINIMAL"},
    "level=low": {"thinking_level": "LOW"},
    "level=high": {"thinking_level": "HIGH"},
    "budget=0": {"thinking_budget": 0},
}


def call(client, model: str, prompt: str, thinking: dict, max_out: int) -> dict:
    cfg = {"temperature": 0.0, "max_output_tokens": max_out}
    if thinking:
        cfg["thinking_config"] = types.ThinkingConfig(**thinking)
    t0 = time.perf_counter()
    try:
        r = client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(**cfg))
    except errors.APIError as e:
        return {"latency_ms": round((time.perf_counter() - t0) * 1000), "error": f"{e.code} {e.status}: {str(e.message)[:200]}"}
    ms = round((time.perf_counter() - t0) * 1000)
    um = r.usage_metadata
    cand = (r.candidates or [None])[0]
    parts = (cand.content.parts if cand and cand.content and cand.content.parts else []) or []
    text = r.text or ""
    return {
        "latency_ms": ms,
        "prompt_tokens": um.prompt_token_count if um else None,
        "candidates_tokens": um.candidates_token_count if um else None,
        "thoughts_tokens": um.thoughts_token_count if um else None,
        "total_tokens": um.total_token_count if um else None,
        "finish_reason": str(cand.finish_reason) if cand else None,
        "n_parts": len(parts),
        "n_thought_parts": sum(1 for p in parts if p.thought),
        "text_chars": len(text),
        "text_head": text[:120],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--gap-s", type=float, default=2.5)
    a = ap.parse_args()
    s = load_settings()
    if not s.gemini_api_key:
        print("Thiếu GEMINI_API_KEY trong .env", file=sys.stderr)
        return 2
    model = a.model or s.model_id
    client = _make_client(s.gemini_api_key, 180)
    prompts = {"short": SHORT, "rag": rag_like_prompt()}
    runs = []
    plan = [(c, p, 512) for c in CONFIGS for p in prompts for _ in range(a.reps)]
    plan.append(("default", "rag", 32))  # trần nhỏ: suy nghĩ có ăn vào max_output_tokens không
    for i, (c, p, mx) in enumerate(plan):
        res = {"config": c, "prompt": p, "max_output_tokens": mx, **call(client, model, prompts[p], CONFIGS[c], mx)}
        runs.append(res)
        print(f"{i + 1}/{len(plan)} {json.dumps(res, ensure_ascii=False)}", flush=True)
        time.sleep(a.gap_s)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {"measured_at": now, "model": model, "sdk": f"google-genai {version('google-genai')}", "temperature": 0.0,
           "prompts": prompts, "configs": CONFIGS, "runs": runs}
    dest = ROOT / "eval" / "results" / f"thinking-probe-{model}-{now[:10]}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
