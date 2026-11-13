# layered-rag-harness

A learning-and-portfolio project: a document Q&A assistant (RAG) with access control and tool calling, built one layer at a time. After each layer, the same fixed question set is re-run, so every layer has to show which failure it fixes.

**Status:** the G0 official answer baseline is still pending. Runtime Tier 1–2 now has an HTTP/OIDC ingress path and intent-to-route-plan code, with contract tests; a live Keycloak check and measured LLM 5a score are still pending. These runtime tiers stop before retrieval or answer generation. See `docs/PLAN.md`, [the runtime API setup](docs/run-api.md), and [the interactive harness flow](docs/architecture/).

## Try the host system (demo)
The harness plugs into a separate synthetic business system, `host/` (orders, tickets, invoices, permissioned search), with a web UI in `web/`. With only Docker and Python installed:
```
python scripts/demo.py up      # builds and starts PostgreSQL, Keycloak, the host API and the web UI; prints the address and test users
python scripts/demo.py down    # stops and removes everything
```
Then open http://localhost:5173 and sign in as `alice` (customer c001): she can read order BM-1001 but not BM-1002, which belongs to another customer, and the answer for a record she may not see is identical to the answer for one that does not exist. The "ask via harness" panel is not connected yet. The demo is local-only (HTTP on loopback, dev-mode Keycloak, throwaway secrets, no persistence). Details: `docs/components/host-web.md`, `host/README.md`.

## Principles
- One layer at a time; a layer is added only if it fixes a failure found by the question set.
- Swappable parts (model provider, search backend, orchestrator, MCP transport) behind adapters, all passing the same contract tests, including "user without permission" cases.
- Only measured numbers are reported, with the conditions they were measured under.
- Parts of the code are written with AI assistance; this is stated openly.

## Layout
- `docs/PLAN.md` — plan, decisions, risks
- `docs/GATES.md` — per-stage checklist (metrics and production concerns)
- `docs/EVAL-SET-DESIGN.md` — fixed question set design
- `docs/BUG-LEDGER.md` — bug ledger
- `docs/components/` — one page per component
- `docs/lab/` — small throwaway experiments (swap one part, record what was learned)
- `docs/PROCESS-LOG.md` — chronological log of how the repo was built, including corrections
- `docs/DATA-CONTRACT.md` — data and permission contract (draft)
- `docs/architecture/` — interactive request lifecycle and design boundaries
- `docs/project-state/` — requested scope, approved decisions, implementation map, and verification gaps
- `eval/intent/` — draft 5a benchmark, route catalog, validator, run and score tools
- `data/corpus/` — synthetic documents (fictional company); `eval/` — question set and consistency check

## Quick start (stage 0)
```
uv sync
uv run pytest
uv run python -m lrh ask "xin chào"   # stub adapter
python eval/validate.py                 # corpus and question-set consistency
```

## Runtime Tier 1–2

The HTTP API requires OIDC issuer/audience/JWKS settings and a domain route catalog. Local Keycloak setup and the `/v1/route` request contract are in [`docs/run-api.md`](docs/run-api.md). The 5a benchmark is still draft-only; its validation and live model run are separate from the existing answer baseline.
