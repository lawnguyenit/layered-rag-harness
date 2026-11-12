"""Load the synthetic corpus into PostgreSQL: `python -m lrh.datastore.seed` (needs DATABASE_URL)."""
from __future__ import annotations

import os
import sys

from lrh.datastore.corpus import load_corpus
from lrh.datastore.postgres import PostgresBusinessStore


def main() -> int:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    count = PostgresBusinessStore(url).seed(load_corpus("data/corpus"))
    print(f"seeded {count} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
