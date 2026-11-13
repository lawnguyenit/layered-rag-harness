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

**Existence-leak convention decided (same day).** Question: when a user lacks permission, should the system say "no information" or "exists but you lack permission"? The owner proposed a refusal on signs of overreach. Analysis: a refusal that differs from the "no information" reply for nonexistent items is itself an existence oracle. Decision: two tiers with two fixed replies. Tier 1 (deterministic): permission filter before retrieval, so every unanswerable question gets the same "not found" reply whether the item is missing or restricted. Tier 2 (behavioural): requests that are overreach by type (other customers' data, claimed roles, system-prompt extraction) get one fixed refusal regardless of whether the target exists. Safety rests on tier 1; tier 2 is defence in depth and is added in stage 3 only if the question set shows a failure.

**Steps 0.1-0.2: synthetic corpus and 40-question set (drafts).** 23 synthetic documents for a fictional meal-kit company (`data/corpus/`, Vietnamese and English, 5 roles, 3 customers with owned records, one customer-written ticket and one partner notice containing planted instructions). 40 questions (`eval/questions.jsonl`: A 8, B 6, C 5, E 13, F 4, G 4; 34 in Vietnamese), generated from `eval/build_questions.py`. `eval/validate.py` checks that corpus and questions agree (asker may read each answer source; key facts appear in the source; forbidden tokens appear only in documents the asker cannot read, so a leak is never mis-scored). The validator was itself tested by deliberately breaking a copy four ways (opening a restricted document, a wrong key fact, a forbidden token planted in a public document, a wrong owner); all four were caught. This checks data consistency only; it does not grade any model answer. Pending: owner review of content, then project skeleton and adapter.

**Steps 0.3-0.4: skeleton and adapter layer (code).** `pyproject.toml` (Python >= 3.11, pydantic, tzdata), `uv.lock`, package `src/lrh/`: adapter contract and error types, a deterministic stub adapter, a sqlite response cache (temperature 0 only), a rate limiter for RPM/TPM/RPD with an injected clock (daily reset at Pacific midnight), a retrying throttle wrapper, a spend guard, a result-record writer and a minimal CLI. 37 tests pass on the stub. Tests were mutation-checked by breaking the limiter and cache on purpose (three breakages, each caught).
**Bug found by a test:** with `SPEND_CAP_USD=0` and a free-tier model, every call was blocked (the check was `spent >= cap`). Fixed by checking the projected cost of a call before making it; logged as B-001 in `docs/BUG-LEDGER.md` with a regression test.
**Limits of this step:** tests were written by the same agent that wrote the code, so they are not yet an independent check; the real Gemini adapter, the token profile and the baseline run are not done; the token-per-character factor is an uncalibrated guess; `uv sync` has not been run on the owner's machine (the lock file was generated on Linux).
**Owner decision:** the owner chose not to review the corpus by hand ("too much for a person to scan"); consistency is checked by `eval/validate.py` instead, which shares the author's blind spots, so independent review by a separate agent is still required before closing stage 0.


**Step 0.5: real Gemini adapter (code, not yet run against the network).** `adapters/gemini.py` (generate and embed through `google-genai`, SDK-internal retries disabled so the throttle counts every attempt), `config.py` (reads `.env`, key hidden from repr), `limits_table.py` (per-model free-tier limits, snapshot 2026-11-08), `factory.py`, CLI `--model <id>`. Two traps handled and tested: `gemini-embedding-2` returns one aggregated vector unless each text is its own content, and an empty model reply raises an error instead of counting as an answer. 48 tests pass with fake clients built from real SDK types; two live tests are skipped unless `LRH_LIVE=1`.
**Limits:** field names were checked by reading SDK 2.33.0, not by a real call. Recognising an exhausted daily quota from "PerDay" in the error is a guess. Next: owner runs the live smoke test and reports the result.

**First run on the owner's machine (same day).** `uv sync` then `uv run pytest`: 48 passed, 2 skipped. Live smoke test (`LRH_LIVE=1 uv run pytest -m live -s`): 2 passed. `gemma-4-31b-it` answered "Hello" in 48 s with 13 prompt tokens and 155 output tokens (thinking included); the embedding call returned one vector per text. One run only, not a latency figure.
**Bug found by `uv sync`:** the committed `uv.lock` predated step 0.5 and pinned none of the new dependencies (google-genai, python-dotenv and 19 transitive packages); uv resolved google-genai 2.34.0 while the code had been checked against 2.33.0. The lock was regenerated on the owner's machine (uv 0.10.6). Logged as B-002.

**Step 0.6: token profile (measured).** `eval/token_profile.py` counts tokens with the `countTokens` API for every corpus document body and every question (63 items), for `gemma-4-31b-it` and `gemini-embedding-2`, and writes `eval/results/token-profile-2026-11-08.json`. Results for Gemma: Vietnamese 2.54 characters per token pooled, English 3.48, lowest 1.81 (invoice documents, which are mostly digits); the embedding model's counts are within 1% of Gemma's. The old guess of 3.0 underestimated 36 of 63 items, which would push real usage past the 16K tokens-per-minute limit. `CHARS_PER_TOKEN` is now 2.0: it overestimates the total by 35% (slower than necessary, but rarely rate-limited); 3 items are still underestimated, by at most 11%. `countTokens` reports the same 13 tokens as the generate call's prompt count, so there is no hidden chat-template overhead.
**Limits:** the corpus is small (5,231 characters), so long RAG prompts may tokenize differently; re-measure once a system prompt and retrieved context exist. Whether `countTokens` counts against the rate limits is not known. The 48 s latency and the thinking tokens are unexplained and must be checked before the baseline run, because thinking may consume `max_output_tokens`.

**Thinking and latency probe (same day).** `eval/probe_thinking.py` made 21 direct calls to `gemma-4-31b-it` (temperature 0) to explain the 48 s smoke-test latency and the 155 output tokens. Results in `eval/results/thinking-probe-gemma-4-31b-it-2026-11-08.json`:
- The model accepts only `thinking_level` MINIMAL or HIGH; LOW and `thinking_budget` return 400. The default behaves like HIGH (identical thinking-token counts: 112 for the one-word prompt, 190 for a short RAG-style prompt). MINIMAL reports no thinking tokens and still answered the RAG-style question correctly.
- Thinking tokens count against `max_output_tokens`: with a cap of 32, 29 went to thinking, the reply was empty and finished with `MAX_TOKENS`. The adapter raised `EmptyResponse`, as intended. The default cap of 1024 was enough for the prompts tried.
- Latency is not explained by thinking: MINIMAL still took 9-30 s for 1-15 output tokens; identical calls varied by up to 2x. Probably free-tier queueing (inference, not verified).
- 2 of 16 valid calls returned `500 INTERNAL`. The throttle only retried 429, so each 500 would have become a failed question in the baseline. **Fixed (B-003):** 500/502/503/504 map to a new `TransientError`, which the throttle retries with exponential backoff. 52 tests pass; disabling the fix makes the two new throttle tests fail. The embedder is not yet wrapped by the throttle, and httpx timeouts are not yet mapped.
**Open decision (owner):** whether the baseline runs with default thinking (HIGH) or MINIMAL. If the level becomes configurable, it must be part of the cache key.

**Experiment: thinking level HIGH vs MINIMAL on all 40 questions (same day).** Owner asked to try both before deciding. Condition: each question sent with every document the asker may read (simulates perfect retrieval plus the tier-1 permission filter), a draft system prompt, `gemma-4-31b-it`, temperature 0. Not the stage-0 baseline. Scripts: `eval/compare_thinking.py`, `eval/summarize_compare.py`; write-up `docs/lab/thinking-level.md`.
- Rule grading: 32/40 at both levels, no leaks. Hand reading by the agent (not yet checked by the owner): HIGH 38/40, MINIMAL 36/40.
- Real differences: on C-005 (not in the documents), MINIMAL answered with an off-topic FAQ line instead of "not found"; on G-003 (English question), MINIMAL replied in Vietnamese. HIGH made neither mistake.
- Cost: MINIMAL used 22 output tokens on average against 417, median latency 18.2 s against 27.3 s, p90 28.6 s against 55.8 s.
- Each level still lost one question to `500 INTERNAL` after three retries (2-4-8 s backoff); retries are not yet split between 429 and 5xx.
- Question-set defects found by reading the failures: A-007, B-005 and B-006 have key facts that a correct answer need not contain. They must be fixed before the baseline run.
**Open decision (owner):** thinking level for the measured track. Agent proposal: HIGH.

## 2026-11-09 — Thinking level decided

**Decision (owner): HIGH thinking for the measured track**, based on `docs/lab/thinking-level.md`. HIGH is now set explicitly per model in `limits_table.py` (equal to the measured default) rather than left to the provider's default, so a silent provider change cannot alter what is measured. The thinking level is part of the cache key (`cache_tag`), so changing it never returns a cached answer from another level. 55 tests pass; removing the level from the cache key makes the new test fail. Not yet checked: whether `gemma-4-26b-a4b-it` accepts HIGH.

## 2026-11-11 — Interactive architecture viewer

**Added** a dependency-free static flow explorer at `docs/architecture/`. It shows the proposed request lifecycle, code/model/data boundaries, stage markers, component details, and three simulated traces (owned order lookup, negated intent, cross-customer lookup). The page labels itself as a design target and links to the current gate checklist so it does not imply that later-stage components are implemented. Added a README entry point and corrected its stale status from “no code yet” to “stage 0 in progress; official baseline pending,” based on the current source tree and `docs/GATES.md`. No application deployment or GitHub Pages hosting was configured.

## 2026-11-11 — Data-flow diagram clarification

**Changed** the architecture viewer's main flow from a component explorer to a concrete data-flow diagram after owner feedback. The SVG now shows the offline corpus/index path and online request path, with named data objects, arrows, decision branches, identity and ACL boundaries, prompt assembly, provider mapping, and current-versus-planned labels. Added a G0 trace so readers can compare today's implemented CLI-to-Gemini path with future RAG/auth examples. This is a documentation artifact; no application feature was implemented. Visual and syntax checks recorded in the commit.

## 2026-11-11 — Architecture diagram layout & interactive redesign

**Rebuilt** `docs/architecture/` (`flow.svg`, `index.html`, `styles.css`, `app.js`) after the owner noted overlapping connectors and cluttered presentation in the previous diagram. Reorganized the online flow into a strict 6-stage grid with dedicated orthogonal routing channels so zero connectors cross through boxes or labels. Inlined the SVG into `index.html` with interactive node selection (showing inputs, outputs, owner, source file, and security rule in a sticky inspector) and live scenario path highlighting (current G0 path, owned-order lookup, Tier-1 cross-customer block, negated/ambiguous intent, and Tier-2 prompt-injection defense), plus a dedicated tab for the 5-role × 7-document-kind ACL matrix from `docs/DATA-CONTRACT.md`. Switched typography to `Be Vietnam Pro` and `JetBrains Mono` for clean Vietnamese diacritic rendering.

## 2026-11-12 — Runtime request path: Tier 1–2

**Implemented** an HTTP `/v1/route` runtime through request limits, OIDC bearer identity, subject-scoped conversation history, intent/slot parsing, deterministic catalog and slot validation, and route-plan decisions. The endpoint returns a route plan and stops before retrieval, ACL enforcement, tools, prompt assembly, or answer generation. Cancellation recognition, multi-task planning, latest compatible entity references, and `no_action` for a solely negated request are explicit owner decisions. The Bếp Mây catalog and 30-case intent set are replaceable fixtures; gold labels remain draft.

**Evidence:** independent run recorded in `docs/project-state/verification.md`: full suite 68 passed, 2 skipped; focused ingress/scorer tests 13 passed; benchmark structure validator accepted 30 rows; `uv lock --check` passed. A live Keycloak flow and live semantic parser score were not run. Input safety currently enforces size/shape/rate only; semantic moderation policy is still open. Process-local rate limiting and local SQLite are not production deployments. See `docs/GATES.md` for remaining runtime and project gates. Source milestone: runtime Tier 1–2 implementation; no deployment performed.

## 2026-11-12 — Intent benchmark v1 draft

**Revised** the 5a evaluation draft after an independent blind review identified inconsistent delivery-status labels, negation annotations, and ambiguous multi-target wording. Preserved v0 unchanged; v1 adds explicit negative candidates, compatible/incompatible reference cases, malformed invoice/ticket IDs, and candidate-level polarity scoring. A second independent review found v1 internally consistent and suitable for owner review as a draft, while identifying remaining coverage limits. The validator now checks top-level/candidate negation consistency and summary polarity. Labels remain draft; the owner has seen v0 and no semantic accuracy is reportable.

**Evidence:** independent verification passes v1 (35 cases) and preserved v0 (30 cases); focused tests pass 14 and the full suite passes 69 with 2 skipped. One Starlette/httpx deprecation warning remains. Live Gemini scoring was not run: no provider key is configured in the environment. Docker Desktop's user application started and its daemon connected, but live Keycloak verification is open because its bootstrap requires local credentials; repo `AGENTS.md` requires asking before accessing `.env` or credential files. The only current route decisions are `route`, `clarify`, `unsupported`, and `no_action`; adding `refuse` to Tier 2 remains pending owner direction. Source milestone `cb7ab3e` is pushed to `origin/main`.

## 2026-11-12 — Parser JSON output smoke finding

**Observed** three draft-only live parser smoke cases fail at structured parsing: Gemma 4 returned text that was not valid JSON, and Pydantic rejected all three before route planning. The provider was reachable, but a follow-up JSON MIME request returned `503 UNAVAILABLE` due temporary high demand. No accuracy claim is made. The evaluation runner previously lost latency/token metadata when schema validation failed; it now retains safe metadata and issue types without storing raw model output. Parser requests JSON MIME output and continues local Pydantic validation.

**Basis:** official [Gemini structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output) describes JSON MIME output and local validation; the current schema’s dynamic slot map uses `additionalProperties`, which the Gemini Developer API rejected in a local SDK validation error. JSON MIME without a schema reached the provider but could not be confirmed because of 503. One live confirmation remains pending. No credential or response body was written to the repository.

**Correction, same date:** after enabling JSON MIME mode and retaining local Pydantic validation, one live `I-001` route smoke passed through parse and planning. Observed condition: `gemma-4-31b-it`, draft-only one-case run, one retry, 38,961 ms, 1,523 prompt tokens, 351 output/thinking tokens. Result remains `draft_preview_not_reportable_as_accuracy`; no test-split evaluation was run. Additional smoke requests are not evidence of accuracy or production latency. Independent checks after this code change: 33 focused tests passed; full suite 73 passed, 2 skipped; v0/v1 validators pass (30/35 draft rows). One Starlette/httpx deprecation warning remains.

**Source milestone:** commit `0f42253`, pushed to `origin/main`.

## 2026-11-12 — Intent v2 diagnostic benchmark and same-turn reference fix

**Added** 22 targeted 5a diagnostic cases and a Vietnamese plain-language review guide; independent blind review found the guide, JSON labels, and catalog conventions consistent. Ran one sequential Gemini diagnostic on the draft set. Of 22 requests, 18 returned the expected top-level decision; 4 failed at the provider boundary (three transient errors and one empty response). Exact slot checks exposed repeated omission of the optional `requested_field`; the strict reference-map metric also disagrees with correct slot provenance in two cases. These findings are preview-only and not a gold score. The report lists the owner decisions still open.

**Fixed** the planner defect exposed by a same-turn reference case: resolve a compatible entity in the current utterance before scanning prior turns, and keep `current_turn` out of the cross-turn references map. Added a regression test.

**Evidence:** independent suite: 74 passed, 2 skipped; v2/v1/v0 validators accept 22/35/30 cases. One Starlette/httpx deprecation warning remains. Diagnostic write-up: `eval/intent/reports/diagnostic-v2-2026-11-12.md`; raw output is ignored under `data/private/`. This is a local checkpoint; commit and push after final review.

## 2026-11-12 — Intent v3 per-task outcomes and final diagnostic

**Decided for this implementation checkpoint** to keep `requested_field` optional but extract it when explicit, evaluate compound requests per intent/target, and derive references from slot provenance. A valid sibling task may be routeable while another task is `clarify` or `unsupported`; the overall plan is `partial`, and `task_outcomes` preserves every disposition. Only `tasks` are dispatchable. These are documented implementation choices for the owner to review; no tool/retrieval action was added.

**Fixed** duplicate raw-ID output using catalog grammars. A model response that repeated a valid ID in both canonical and `*_raw` slots is normalized before scoring; identical malformed raw/canonical strings keep only the raw slot. Unknown sentinel outcomes now carry `out_of_scope`.

**Evidence:** independent reviewer validated v3 labels/docs. Independent tests: 75 passed, 2 skipped; v3/v2/v1/v0 validators accept 22/22/35/30 rows. One Gemini call per v3 case was attempted: 20 responses matched decision, route tasks and task outcomes; two provider `TransientError`s (D-004/D-011). After deterministic output normalization and plan replay, candidate exact, route-task exact, and task-outcome exact are each 20/22; reference, plan ambiguity and missing-slot exact are 22/22; false/wrong dispatch are 0/0. This remains draft-only. Report: `eval/intent/reports/diagnostic-v3-2026-11-12.md`.

## 2026-11-12 — Local Keycloak OIDC smoke

**Verified** a temporary Keycloak 26.8.2 realm bound to loopback. A real RS256 access token was acquired; Uvicorn received HTTP requests on loopback while the verifier validated the signature from live JWKS, issuer, audience, and role. The route rejected a missing bearer (401), rejected a caller-supplied role (422), and accepted the valid token (200), deriving the customer role and owner scope from token claims.

**Limit:** this was a local HTTP integration smoke, not production readiness. The temporary smoke client used the direct access grant and a hardcoded `customer_id` claim after the test user's custom attribute was not persisted; per-user attribute mapping, Authorization Code + PKCE, and production deployment remain unverified. The temporary container and generated smoke artifacts are excluded from Git. Verification state and remaining gates are recorded in `docs/project-state/verification.md` and `docs/GATES.md`.

## 2026-11-12 — Local OIDC Authorization Code + PKCE smoke

**Verified** a second loopback-only Keycloak/Uvicorn flow using Authorization Code + PKCE S256. The public client had direct grants disabled; returned state was checked; the API audience and customer role were present; a test-only Keycloak username property mapper produced `customer_id=c001`; the real HTTP route returned 200 with owner scope `c001`.

**Limit:** the local `httpx` test client manually allowed Secure cookies over loopback HTTP because it does not mirror browser localhost trust behavior. This only exercises a local test flow; production must use HTTPS. The mapper is not a production identity design, and data-store ACL enforcement remains untested. Details: `docs/lab/auth-pkce-smoke-2026-11-12.md`.

## 2026-11-12 — Semantic input-safety probe and documentation correction

**Probed** Gemini API `BLOCK_ONLY_HIGH` safety settings on the configured Gemma 4 parser call with synthetic harmful requests and benign support reports. Three direct harmful examples were not blocked and returned `NEGLIGIBLE` ratings; two benign reports were allowed; a negated-help sample encountered transient provider failures. A separate Gemini 3.8 Flash classifier probe produced only repeated `ServerError`s and no labels. These are exploratory observations, not a benchmark. The provider-native Gemma filter is therefore not accepted as the ingress enforcement gate; the semantic safety gate remains open. Details and dated official sources: `docs/lab/input-safety-probe-2026-11-12.md`.

**Corrected** the historical v2 owner-readable guide, which still described all-or-nothing outcomes for D-010/D-011. It now explicitly marks those expectations as superseded by the v3/runtime `partial` behavior; the original v2 JSONL and diagnostic report remain preserved as historical artifacts.

## 2026-11-12 — v1 intent diagnostic and scorer reliability

**Ran** all 29 cases in the v1 `test` split against the configured Gemini parser using synthetic draft data. Independent review confirmed 29/29 prediction IDs with two `TransientError`s. The readable preview report records end-to-end and conditional metrics separately; it is not an accuracy claim because the labels are draft and the split was used during development.

**Fixed** scorer errors found in that review: unavailable parse/plan results no longer earn exact-match credit for empty/default fields, provider failures no longer get semantic parse-error labels, conditional metrics are shown beside end-to-end values, and default CLI JSON uses portable escaped Unicode on Windows. Independent tests: focused scoring = 7 passed; full suite = 78 passed, 2 skipped. One existing Starlette/httpx deprecation warning remains. See `docs/BUG-LEDGER.md` B-010/B-011 and `eval/intent/reports/diagnostic-v1-test-2026-11-12.md`.

## 2026-11-13 — G0 question-set fixes and H1 business store

**Fixed** the three question-set defects flagged before the baseline: A-007 now accepts "300.000|300.001" (the policy text says 300.001), B-005 expects the third-complaint fact instead of a phrase already in the question, B-006 drops the unneeded date. Regenerated `eval/questions.jsonl`; validator passes. Baseline run and hand grading are still pending (needs the provider key, which the agent does not read).

**Added** H1 of `docs/HOST-SYSTEM-PLAN.md`: `BusinessStore` contract with in-memory and PostgreSQL adapters, Alembic migration `0001`, synthetic corpus seeding, `compose.db.yaml` (postgres:16-alpine, loopback port 55432). Both adapters pass the same contract tests including the no-access cases (30 passed); breaking the owner condition in the SQL makes 3 tests fail. Full suite with Postgres enabled: 108 passed, 2 skipped. Not done: wiring into the API, a role separated from the database owner and row-level security (H2, owner to write), connection pooling. No credentials stored; the test database password was generated per run.

## 2026-11-13 — Host system split from the harness

**Changed** the layout: the business-record store, Alembic migration, compose file, token verification and read-only API now live in `host/`, a separate uv project (`bepmay-host`) with its own dependencies, tests and README. The harness keeps only a port and an HTTP client (`src/lrh/business.py`) that forwards the caller's bearer token; it no longer depends on psycopg or Alembic. Reason (owner direction): show readers that the host system is a separate thing the harness plugs into, rather than building as if one team controlled everything. The host verifies tokens for its own audience, owns the access rule, and returns the same 404 for denied and nonexistent records.

**Evidence:** harness suite 83 passed, 2 skipped; host suite 35 passed including the Postgres adapter on a throwaway container (removed afterwards). Both `uv lock --check` pass. **Not verified:** a live Keycloak token accepted by both services (needs both audiences or token exchange), the harness calling the host over a real socket, row-level security (H2).

**Removed** untracked artifacts nothing referenced: `output/` (diagram screenshots), `.playwright-cli/`, empty `scripts/data/`.
