"""Set the app role's password: `python -m bepmay_host.provision` (env: MIGRATE_DATABASE_URL, HOST_APP_PASSWORD).

Role passwords cannot be bound parameters in ALTER ROLE, so the value is quoted with psycopg.sql.Literal.
The password never lives in a migration or in the repo.
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg import sql

from bepmay_host.seed import owner_url


def main() -> int:
    url, password = owner_url(), os.getenv("HOST_APP_PASSWORD", "")
    if not url or not password:
        print("MIGRATE_DATABASE_URL and HOST_APP_PASSWORD are required", file=sys.stderr)
        return 2
    with psycopg.connect(url, connect_timeout=3) as conn:
        conn.execute(sql.SQL("ALTER ROLE bepmay_app PASSWORD {}").format(sql.Literal(password)))
    print("app role password set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
