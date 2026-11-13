"""One-command local demo of the host system: `python scripts/demo.py up` / `down` / `status`.

Needs only Docker (with Compose) and Python 3. `up` generates throwaway secrets for this run, builds and starts
PostgreSQL+pgvector, Keycloak (dev mode), the host API and the web UI from compose.demo.yaml, creates a Keycloak realm
with synthetic users, checks that everything answers, and prints the addresses and the shared dev password once.
Nothing is written to disk and no data persists. This is a demo, not a deployment (HTTP on loopback, dev-mode Keycloak).
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "compose.demo.yaml")]
UI, HOST, KEYCLOAK = "http://localhost:5173", "http://127.0.0.1:8020", "http://localhost:18080"
REALM = "bepmay-e2e"
USERS = [
    ("alice", "khách hàng c001", "thấy đơn BM-1001, không thấy BM-1002 (của c002)"),
    ("bob", "khách hàng c002", "thấy đơn BM-1002, không thấy BM-1001"),
    ("sam", "nhân viên hỗ trợ", "thấy đơn và phiếu, không thấy hóa đơn"),
    ("fin", "tài chính", "thấy hóa đơn, không thấy phiếu hỗ trợ"),
    ("mia", "quản lý", "thấy mọi thứ, kể cả tài liệu nội bộ"),
]


def run(args: list[str], env: dict[str, str], check: bool = True) -> int:
    r = subprocess.run(args, env=env, cwd=ROOT)
    if check and r.returncode:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(args[:6])} ...")
    return r.returncode


def get(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:  # 4xx/5xx are answers, not silence
        return e.code, b""
    except Exception:
        return 0, b""


def wait_for(label: str, url: str, seconds: int = 120) -> None:
    for _ in range(seconds):
        if get(url)[0] == 200:
            return
        time.sleep(1)
    raise SystemExit(f"{label} did not answer at {url} within {seconds}s")


def docker_ready() -> None:
    if subprocess.run(["docker", "info"], capture_output=True).returncode:
        raise SystemExit("Docker is not running. Start Docker Desktop and try again.")


def up(password: str | None) -> int:
    docker_ready()
    secrets_env = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
        "HOST_APP_PASSWORD": secrets.token_urlsafe(18),
        "KC_ADMIN_PASSWORD": secrets.token_urlsafe(18),
        "DEV_USER_PASSWORD": password or secrets.token_urlsafe(9),
    }
    env = {**os.environ, **secrets_env}
    print("Clearing any previous demo run (the demo keeps no data)...")
    run(COMPOSE + ["--profile", "setup", "down", "-v", "--remove-orphans"], {**os.environ, **{k: "unused" for k in secrets_env}}, check=False)
    print("Building and starting PostgreSQL, Keycloak, the host API and the web UI (first run downloads images)...")
    run(COMPOSE + ["up", "-d", "--build", "--wait"], env)
    print("Creating the Keycloak realm and synthetic users...")
    run(COMPOSE + ["--profile", "setup", "run", "--rm", "demo-setup"], env)

    # Do not claim success before looking.
    wait_for("web UI", UI + "/")
    wait_for("host API", HOST + "/healthz")
    status, body = get(f"{KEYCLOAK}/realms/{REALM}/.well-known/openid-configuration")
    if status != 200 or json.loads(body).get("issuer") != f"{KEYCLOAK}/realms/{REALM}":
        raise SystemExit("Keycloak realm is up but its issuer does not match what the host expects; do not use this stack.")
    status, _ = get(HOST + "/v1/orders/BM-1001")
    if status != 401:
        raise SystemExit(f"host API should refuse an unauthenticated request with 401, got {status}")

    pw = secrets_env["DEV_USER_PASSWORD"]
    print(f"""
Demo is running.

  Web UI           {UI}     <- start here

To see the demo, click "Đăng nhập bằng Keycloak" on the web UI and sign in with one of these users.
They share one throwaway password: {pw}

""" + "\n".join(f"  {u:6} {role:18} {what}" for u, role, what in USERS) + f"""

Try: sign in as alice and look up order BM-1001, then BM-1002; sign in as bob and compare; search "staffing plan"
as mia (manager) and as sam (support). The "ask via harness" panel is not connected yet.

Not needed to see the demo (the `admin` account does NOT work on the web UI sign-in page):
  Keycloak admin console   {KEYCLOAK}   user: admin   password: {secrets_env['KC_ADMIN_PASSWORD']}
  Host API docs            {HOST}/docs   (needs a bearer token)

Stop and remove everything:  python scripts/demo.py down
(Secrets are generated per run and are not stored. Rerun `up` for a new set.)""")
    return 0


def down() -> int:
    docker_ready()
    placeholders = {k: "unused" for k in ("POSTGRES_PASSWORD", "HOST_APP_PASSWORD", "KC_ADMIN_PASSWORD", "DEV_USER_PASSWORD")}
    run(COMPOSE + ["--profile", "setup", "down", "-v", "--remove-orphans"], {**os.environ, **placeholders})
    print("Demo stopped and removed.")
    return 0


def status() -> int:
    for label, url in (("web UI", UI + "/"), ("host API", HOST + "/healthz"), ("Keycloak realm", f"{KEYCLOAK}/realms/{REALM}")):
        print(f"{'up  ' if get(url)[0] == 200 else 'down'} {label:15} {url}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["up", "down", "status"])
    ap.add_argument("--password", help="choose the shared dev password (default: a random one)")
    a = ap.parse_args()
    sys.exit({"up": lambda: up(a.password), "down": down, "status": status}[a.command]())
