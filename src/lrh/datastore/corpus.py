"""Parse data/corpus/*.md (frontmatter + body) into rows. Synthetic data only."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_REF = {
    "order": re.compile(r"\bBM-\d{4}\b"),
    "ticket": re.compile(r"\bT\d{2}\b"),
    "invoice": re.compile(r"\bINV-\d{4}-\d{4}\b"),
}


@dataclass(frozen=True)
class CorpusDoc:
    doc_id: str
    kind: str
    title: str
    body: str
    allowed_roles: tuple[str, ...]
    owner_customer_id: str | None
    ref_id: str | None


def parse_doc(text: str) -> CorpusDoc:
    head, sep, body = text.partition("\n---\n")
    if not head.startswith("---") or not sep:
        raise ValueError("corpus file must start with a --- frontmatter block")
    meta: dict[str, str] = {}
    for line in head.splitlines()[1:]:
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    roles = tuple(r.strip() for r in meta["allowed_roles"].strip("[]").split(",") if r.strip())
    kind = meta["kind"]
    pattern = _REF.get(kind)
    match = pattern.search(meta["title"]) if pattern else None
    return CorpusDoc(
        doc_id=meta["doc_id"],
        kind=kind,
        title=meta["title"],
        body=body.strip(),
        allowed_roles=roles,
        owner_customer_id=meta.get("owner_customer_id") or None,
        ref_id=match.group(0) if match else None,
    )


def load_corpus(directory: str | Path) -> list[CorpusDoc]:
    return [parse_doc(p.read_text(encoding="utf-8").replace("\r\n", "\n")) for p in sorted(Path(directory).glob("*.md"))]
