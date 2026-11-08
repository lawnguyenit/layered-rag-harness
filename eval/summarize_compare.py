"""Tổng hợp kết quả eval/compare_thinking.py thành báo cáo markdown đặt cạnh nhau.

    uv run python eval/summarize_compare.py [--date 2026-11-08] [--levels HIGH MINIMAL]
Ghi eval/results/thinking-compare-<ngày>.md. Điểm ở đây chấm bằng luật; câu lệch giữa hai mức phải đọc tay.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(level: str, d: str) -> dict[str, dict]:
    p = ROOT / "eval" / "results" / f"thinking-compare-{level.lower()}-{d}.jsonl"
    recs = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            recs[r["question_id"]] = r  # bản ghi sau thắng (chạy lại)
    return recs


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def cell(s: str | None, n: int = 160) -> str:
    return "(lỗi)" if s is None else s.replace("\n", " ").replace("|", "\\|")[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(date.today()))
    ap.add_argument("--levels", nargs=2, default=["HIGH", "MINIMAL"])
    a = ap.parse_args()
    qs = {json.loads(ln)["id"]: json.loads(ln) for ln in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()}
    L = a.levels
    R = {lv: load(lv, a.date) for lv in L}
    out = [f"# So mức suy nghĩ: {L[0]} và {L[1]} ({a.date})", "",
           "Thí nghiệm, không phải điểm gốc. Mô hình gemma-4-31b-it, temperature 0, max_output_tokens 1024. "
           "Mỗi câu kèm toàn bộ tài liệu người hỏi được đọc (mô phỏng truy xuất hoàn hảo + lọc quyền tầng 1). "
           "System prompt bản nháp trong eval/compare_thinking.py. Chấm bằng luật (key_facts, must_not_contain, hai câu cố định); G-002, G-003 chấm tay.", ""]
    out += ["## Tóm tắt", "", f"| Chỉ số | {L[0]} | {L[1]} |", "|---|---|---|"]
    def row(name, f):
        out.append(f"| {name} | {f(R[L[0]])} | {f(R[L[1]])} |")
    row("Số câu có kết quả", lambda r: len(r))
    for v in ("pass", "fail", "false_refusal", "wrong_class", "leak", "error", "na"):
        row(v, lambda r, v=v: sum(1 for x in r.values() if x["verdict"] == v))
    lat = lambda r: [x["latency_ms"] / 1000 for x in r.values() if x.get("latency_ms")]
    row("Độ trễ trung vị (s)", lambda r: f"{statistics.median(lat(r)):.1f}")
    row("Độ trễ p90 (s)", lambda r: f"{pct(lat(r), 0.9):.1f}")
    tok = lambda r: [x["output_tokens"] for x in r.values() if x.get("output_tokens") is not None]
    row("Token ra trung bình (gồm suy nghĩ)", lambda r: f"{statistics.mean(tok(r)):.0f}")
    row("Token ra tối đa", lambda r: max(tok(r)))
    row("Tổng token (vào + ra)", lambda r: sum(x.get("prompt_tokens", 0) + x.get("output_tokens", 0) for x in r.values()))
    row("Lần thử lại", lambda r: sum(x.get("retries", 0) for x in r.values()))
    # cặp pair_with phải cùng lớp
    pairs = sorted({tuple(sorted((i, q["expected"]["pair_with"]))) for i, q in qs.items() if "pair_with" in q["expected"]})
    row("Cặp pair_with cùng lớp", lambda r: f"{sum(1 for x, y in pairs if x in r and y in r and r[x].get('class') == r[y].get('class'))}/{len(pairs)}")
    out += ["", "## Theo nhóm (pass / tổng)", "", f"| Nhóm | {L[0]} | {L[1]} |", "|---|---|---|"]
    for g in sorted({q["group"] for q in qs.values()}):
        ids = [i for i, q in qs.items() if q["group"] == g]
        f = lambda r: f"{sum(1 for i in ids if r.get(i, {}).get('verdict') == 'pass')}/{len(ids)}"
        out.append(f"| {g} | {f(R[L[0]])} | {f(R[L[1]])} |")
    diff = [i for i in qs if R[L[0]].get(i, {}).get("verdict") != R[L[1]].get(i, {}).get("verdict")]
    out += ["", f"## Câu cho kết quả khác nhau ({len(diff)})", ""]
    for i in diff:
        q = qs[i]
        out.append(f"**{i}** ({q['asker']['role']}) {q['question']}  ")
        out.append(f"Kỳ vọng: {q['expected']['type']} {q['expected'].get('expected_class', '')} {q['expected']['key_facts'] or ''}  ")
        for lv in L:
            x = R[lv].get(i, {})
            out.append(f"- {lv} [{x.get('verdict')}; thiếu {x.get('missing_facts') or '-'}]: {cell(x.get('answer'), 400)}")
        out.append("")
    out += ["## Mọi câu, đặt cạnh nhau", "", f"| ID | {L[0]} | {L[1]} | {L[0]} trả lời | {L[1]} trả lời |", "|---|---|---|---|---|"]
    for i in qs:
        a0, a1 = R[L[0]].get(i, {}), R[L[1]].get(i, {})
        out.append(f"| {i} | {a0.get('verdict')} | {a1.get('verdict')} | {cell(a0.get('answer'))} | {cell(a1.get('answer'))} |")
    dest = ROOT / "eval" / "results" / f"thinking-compare-{a.date}.md"
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[: out.index("## Mọi câu, đặt cạnh nhau")]))
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
