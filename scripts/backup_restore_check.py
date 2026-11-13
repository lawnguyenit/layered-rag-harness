"""Backup and restore drill for the host database, using throwaway Docker containers.

Proves what a dump has to carry for the access rule to survive a restore:
  1. source: migrate + provision + seed + ingest into a fresh pgvector container
  2. dump: `pg_dumpall --roles-only` (roles and password hashes) and `pg_dump -Fc` (schema, data, RLS, policies, grants)
  3. restore both into a second EMPTY container, then run the host's own RLS / contract / search tests against it
  4. negative control: restore only the database dump (the default `pg_dump` habit) into a third empty container
     and show that the app role and policies are missing, i.e. the trap this drill exists to catch.
Run from the repo root: `uv run python scripts/backup_restore_check.py` (needs Docker and `uv`). Nothing persists.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IMAGE = "pgvector/pgvector:pg16"
HOST_DIR = Path(__file__).resolve().parents[1] / "host"
RUN = secrets.token_hex(3)


def sh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def start(name: str, password: str, db: str) -> int:
    sh("docker", "run", "-d", "--name", name, "-e", "POSTGRES_USER=lrh", "-e", f"POSTGRES_PASSWORD={password}",
       "-e", f"POSTGRES_DB={db}", "-p", "127.0.0.1::5432", IMAGE)
    for _ in range(60):
        if sh("docker", "exec", name, "pg_isready", "-U", "lrh", "-d", db, check=False).returncode == 0:
            time.sleep(1)  # the entrypoint restarts the server once after init
            if sh("docker", "exec", name, "pg_isready", "-U", "lrh", "-d", db, check=False).returncode == 0:
                break
        time.sleep(1)
    else:
        raise SystemExit(f"{name} did not become ready")
    mapped = sh("docker", "port", name, "5432/tcp").stdout.strip().splitlines()[0]
    return int(mapped.rsplit(":", 1)[1])


def psql(name: str, db: str, sql: str) -> str:
    return sh("docker", "exec", name, "psql", "-U", "lrh", "-d", db, "-Atc", sql).stdout.strip()


def host_cmd(*cmd: str, env: dict[str, str]) -> None:
    r = subprocess.run(["uv", "run", *cmd], cwd=HOST_DIR, env={**os.environ, **env}, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{r.stdout[-800:]}\n{r.stderr[-800:]}")


def main() -> int:
    owner_pw, app_pw = secrets.token_urlsafe(12), secrets.token_urlsafe(12)
    names = {k: f"lrh-drill-{k}-{RUN}" for k in ("src", "dst", "ctl")}
    failures: list[str] = []
    try:
        port = start(names["src"], owner_pw, "lrh")
        src_owner = f"postgresql://lrh:{owner_pw}@127.0.0.1:{port}/lrh"
        env = {"MIGRATE_DATABASE_URL": src_owner, "HOST_APP_PASSWORD": app_pw, "HOST_EMBEDDER": "hash",
               "HOST_CORPUS_DIR": str(HOST_DIR.parent / "data" / "corpus")}
        for cmd in (("alembic", "upgrade", "head"), ("python", "-m", "bepmay_host.provision"),
                    ("python", "-m", "bepmay_host.seed"), ("python", "-m", "bepmay_host.ingest")):
            host_cmd(*cmd, env=env)
        counts = {t: psql(names["src"], "lrh", f"SELECT count(*) FROM {t}") for t in ("records", "chunks")}
        print(f"source ready: {counts}")

        with tempfile.TemporaryDirectory() as tmp:
            roles_file, db_file = Path(tmp, "roles.sql"), Path(tmp, "lrh.dump")
            with open(roles_file, "wb") as f:
                subprocess.run(["docker", "exec", names["src"], "pg_dumpall", "-U", "lrh", "--roles-only"], stdout=f, check=True)
            with open(db_file, "wb") as f:
                subprocess.run(["docker", "exec", names["src"], "pg_dump", "-U", "lrh", "-Fc", "lrh"], stdout=f, check=True)
            print(f"dumped: roles {roles_file.stat().st_size} bytes, database {db_file.stat().st_size} bytes")

            # --- restore with roles ---
            dport = start(names["dst"], owner_pw, "postgres")
            with open(roles_file, "rb") as f:  # `lrh` already exists in the target, so that one statement errors: expected
                subprocess.run(["docker", "exec", "-i", names["dst"], "psql", "-U", "lrh", "-d", "postgres", "-q"], stdin=f,
                               capture_output=True, check=False)
            with open(db_file, "rb") as f:
                r = subprocess.run(["docker", "exec", "-i", names["dst"], "pg_restore", "-U", "lrh", "-C", "-d", "postgres",
                                    "--exit-on-error"], stdin=f, capture_output=True)
            if r.returncode:
                failures.append("pg_restore with roles failed: " + r.stderr.decode(errors="replace")[-300:])
            checks = {
                "app role exists, not superuser, no BYPASSRLS": psql(names["dst"], "lrh", "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='bepmay_app'") == "f|f",
                "RLS enabled and forced on records and chunks": psql(names["dst"], "lrh", "SELECT count(*) FROM pg_class WHERE relname IN ('records','chunks') AND relrowsecurity AND relforcerowsecurity") == "2",
                "both policies present": psql(names["dst"], "lrh", "SELECT count(*) FROM pg_policies WHERE policyname IN ('records_visible','chunks_visible')") == "2",
                "row counts equal to source": {t: psql(names["dst"], "lrh", f"SELECT count(*) FROM {t}") for t in ("records", "chunks")} == counts,
            }
            for label, ok in checks.items():
                print(("ok   " if ok else "FAIL ") + "restored: " + label)
                if not ok:
                    failures.append(label)
            dst_owner = f"postgresql://lrh:{owner_pw}@127.0.0.1:{dport}/lrh"
            dst_app = f"postgresql://bepmay_app:{app_pw}@127.0.0.1:{dport}/lrh"
            t = subprocess.run(["uv", "run", "pytest", "-q", "tests/test_rls.py", "tests/test_store_contract.py", "tests/test_search.py"],
                               cwd=HOST_DIR, capture_output=True, text=True,
                               env={**os.environ, "HOST_TEST_DATABASE_URL": dst_owner, "HOST_TEST_APP_DATABASE_URL": dst_app})
            summary = [ln for ln in t.stdout.splitlines() if "passed" in ln or "failed" in ln]
            print(("ok   " if t.returncode == 0 else "FAIL ") + "host RLS/contract/search tests on the restored database (app role, original password): " + (summary[-1] if summary else t.stdout[-200:]))
            if t.returncode:
                failures.append("host tests on restored database")

            # --- negative control: database dump only, no roles ---
            start(names["ctl"], owner_pw, "postgres")
            with open(db_file, "rb") as f:
                r = subprocess.run(["docker", "exec", "-i", names["ctl"], "pg_restore", "-U", "lrh", "-C", "-d", "postgres"],
                                   stdin=f, capture_output=True)
            role_there = psql(names["ctl"], "lrh", "SELECT count(*) FROM pg_roles WHERE rolname='bepmay_app'")
            policies = psql(names["ctl"], "lrh", "SELECT count(*) FROM pg_policies")
            trap = role_there == "0" and r.returncode != 0
            print(("ok   " if trap else "FAIL ") + f"control (database dump without roles): app role count={role_there}, policies={policies}, "
                  f"pg_restore exit={r.returncode}: the trap is real")
            if not trap:
                failures.append("negative control did not show the trap")
    finally:
        for n in names.values():
            subprocess.run(["docker", "rm", "-f", n], capture_output=True)
    print("\nRESULT:", "PASS" if not failures else "FAIL: " + "; ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
