# Process log

A chronological record of how this repository was built: what changed, why, and what was corrected. Written for readers of the repo. Working documents under `docs/` are in Vietnamese; this log and the README are in English.

**AI assistance:** the plan, documents and code are drafted with an AI assistant (Claude) in the owner's sessions. The owner decides, reviews, runs everything that touches real services, and is intended to hand-write the core loop and the permission filter (proposed, not yet confirmed). Numbers are recorded only when measured, with their conditions.

**Rule:** append one entry per working session (date, what changed, why, evidence). Corrections go in as their own lines, not by rewriting history.

---

## 2026-11-08 — Planning and scaffold

**Goal set.** A portfolio project: a document Q&A assistant (RAG) with access control and tool calling (MCP), built one layer at a time. A layer is added only if it fixes a failure found by a fixed question set. Two tracks: a product track (one stack, deep, measured) and a lab track (small experiments swapping one part behind an adapter).

**Stack evidence.** A sample of about 17 public freelance job descriptions was read to choose a stack. It suggests Python, FastAPI, PostgreSQL with pgvector, and Docker. This is a proposal, not yet confirmed by the owner. (`docs/PLAN.md` section 2)

**Scaffold** — commit `4ef8266`: agent rules (`AGENTS.md`, single source; `CLAUDE.md` and `GEMINI.md` only point to it), plan, per-stage gates (`docs/GATES.md`), evaluation-set design, bug ledger, component and lab templates. No source code yet.

**Environment probe** — commits `7756274`, `a98a5d2`. A read-only PowerShell script (`scripts/probe-env.ps1`) was run on the owner's machine. Findings: Docker Desktop and WSL2 are running; Python 3.13, uv, Node 22 present; no pgvector image locally; port 8000 already in use, so the API will not use it. Two small defects in the first version were fixed: output was written relative to the current directory, and `.gitignore` only covered `data/private/` at the repo root.

**Model provider planning** — commits `2cbb802` to `2150f87`. The direction changed several times, each time on evidence:
1. First plan: Gemini for development, Claude for final measurement, and optionally local models. The owner dropped local models.
2. The owner then restricted the project to free tiers. Claude was removed (no free API tier found; trial credits not checked).
3. Pricing and rate-limit documentation was read. **Correction:** an early conclusion that the pricing page lacked "Gemini 3.8 Flash" came from a partial read (100,000 of 106,069 characters); the rate-limit page lists those models, so the conclusion was withdrawn (`6ad6961`).
4. The documentation does not publish per-model free-tier numbers; they are only visible in the account's AI Studio page. The owner supplied screenshots. Measured on this account on 2026-11-08: Gemini 3.8 Flash 5 RPM / 250K TPM / 20 RPD; Gemma 4 31B and 26B 30 RPM / 16K TPM / 14,400 RPD; embeddings 100 RPM / 30K TPM / 1,000 RPD.
5. Consequence: 20 requests per day cannot support an iterate-and-measure loop, so **Gemma 4 31B is the main development and measurement model**, Gemma 4 26B the fallback, Gemini 3.8 Flash a reference on a subset. Gemma 4 runs on Google's servers through the same API (it is not a local model). Every reported number must name the model.
6. Free-tier content may be used by the provider to improve its products, so only synthetic or public data is sent.

**Stage 0 rules derived from the limits:** a deterministic stub adapter for tests, a response cache keyed by model and prompt, rate limiting by both requests and tokens, resumable runs across days, deterministic grading first with a hand-graded sample, no model mixing inside one measurement.

**Why the question set exists before RAG.** A baseline run without documents is the control: it shows which questions fail without retrieval, so stage 1 can show what retrieval fixes.

**Open decisions** (owner): stack confirmation, who hand-writes the core, the synthetic corpus, the permission convention for restricted documents, number of roles. Step 0.0 (`docs/DATA-CONTRACT.md`) was added after the owner pointed out that the corpus and questions depend on a data and permission contract that did not yet exist.

**Next:** review `docs/DATA-CONTRACT.md`, then write the synthetic corpus and the 40-question set, then the project skeleton and adapter contract.

**Direction change: customer-facing context (same day, later).** The first corpus idea was an internal company handbook with employee roles, chosen because permission cases are easy to build; the audience had not been asked. The owner pointed out that the clients in the job sample are companies whose *customers* use the system. The job sample supports this: roughly 5 of 17 descriptions mention tenant isolation or access control, and one asks how to stop an assistant from reaching other customers' data (small, keyword-biased sample). Decision: the asker is a customer, with extra internal roles added so that need-to-know isolation is demonstrated. Proposed roles: `visitor`, `customer` (own records only), `support`, `finance` (lateral to support), `manager` (listed explicitly on both). Added: identity comes from the authenticated session, never from the question text; every blocked case gets a positive control to measure false refusals. `docs/DATA-CONTRACT.md` rewritten as v2 and `docs/EVAL-SET-DESIGN.md` updated. Still open: the role set, the existence-confirmation convention, and whether support sees all customers' records.
