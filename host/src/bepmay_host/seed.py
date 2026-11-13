"""Load the synthetic corpus into PostgreSQL: `python -m bepmay_host.seed` (needs DATABASE_URL)."""
from __future__ import annotations

import os
import sys

from bepmay_host.corpus import load_corpus
from bepmay_host.postgres_store import PostgresBusinessStore


def main() -> int:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    count = PostgresBusinessStore(url).seed(load_corpus(os.getenv("HOST_CORPUS_DIR", "../data/corpus")))
    print(f"seeded {count} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
