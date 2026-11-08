"""Bước 0.6: hồ sơ token. Đếm token thật (API countTokens) cho từng tài liệu corpus và từng câu hỏi,
so với số ký tự, để thay hệ số đoán CHARS_PER_TOKEN bằng số đo.

Chạy trên máy chủ repo (cần GEMINI_API_KEY trong .env):
    uv run python eval/token_profile.py [--models gemma-4-31b-it gemini-embedding-2]
Ghi kết quả vào eval/results/token-profile-<ngày>.json (chỉ dữ liệu tổng hợp, không có khóa).
countTokens có tính vào RPD hay không: chưa kiểm. Script giãn cách theo RPM thấp nhất (30/phút) cho an toàn.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lrh.adapters.gemini import _make_client  # noqa: E402
from lrh.config import load_settings  # noqa: E402
from lrh.contracts import CHARS_PER_TOKEN  # noqa: E402


def split_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, fm, body = raw.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body.strip()


def load_items() -> list[dict]:
    items = []
    for p in sorted((ROOT / "data" / "corpus").glob("*.md")):
        meta, body = split_frontmatter(p.read_text(encoding="utf-8"))
        items.append({"kind": "doc", "id": meta.get("doc_id", p.stem), "lang": meta.get("language", "?"), "text": body})
    for line in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            items.append({"kind": "question", "id": q["id"], "lang": q["lang"], "text": q["question"]})
    return items


def summarize(rows: list[dict]) -> dict:
    ratios = sorted(r["chars"] / r["tokens"] for r in rows)
    chars, tokens = sum(r["chars"] for r in rows), sum(r["tokens"] for r in rows)
    under = sum(1 for r in rows if math.ceil(r["chars"] / CHARS_PER_TOKEN) < r["tokens"])
    return {
        "n": len(rows),
        "chars": chars,
        "tokens": tokens,
        "pooled_chars_per_token": round(chars / tokens, 3),
        "min_chars_per_token": round(ratios[0], 3),
        "median_chars_per_token": round(statistics.median(ratios), 3),
        "max_chars_per_token": round(ratios[-1], 3),
        f"underestimated_at_{CHARS_PER_TOKEN}": under,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--gap-s", type=float, default=2.1, help="giãn cách giữa hai lượt gọi (30 RPM -> 2 s)")
    args = ap.parse_args()
    s = load_settings()
    if not s.gemini_api_key:
        print("Thiếu GEMINI_API_KEY trong .env", file=sys.stderr)
        return 2
    models = args.models or [s.model_id, s.embedding_model_id]
    client = _make_client(s.gemini_api_key, 60)
    items = load_items()
    out = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
        "sdk": f"google-genai {version('google-genai')}",
        "method": "models.count_tokens on the document body (frontmatter removed) or the question text, one call per item",
        "chars_per_token_in_code_at_measurement": CHARS_PER_TOKEN,
        "models": {},
    }
    for m in models:
        rows = []
        for i, it in enumerate(items):
            r = client.models.count_tokens(model=m, contents=it["text"])
            rows.append({"kind": it["kind"], "id": it["id"], "lang": it["lang"], "chars": len(it["text"]), "tokens": r.total_tokens})
            print(f"{m} {i + 1}/{len(items)} {it['id']} {len(it['text'])}c {r.total_tokens}t", flush=True)
            time.sleep(args.gap_s)
        groups = {"all": rows}
        for lang in sorted({r["lang"] for r in rows}):
            groups[f"lang={lang}"] = [r for r in rows if r["lang"] == lang]
        for kind in ("doc", "question"):
            groups[f"kind={kind}"] = [r for r in rows if r["kind"] == kind]
        out["models"][m] = {"summary": {k: summarize(v) for k, v in groups.items() if v}, "items": rows}
    dest = ROOT / "eval" / "results" / f"token-profile-{out['measured_at'][:10]}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({m: v["summary"] for m, v in out["models"].items()}, ensure_ascii=False, indent=2))
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
