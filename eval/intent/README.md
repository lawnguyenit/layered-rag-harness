# Intent, slot, and uncertainty evaluation (draft versions)

**Status:** v0–v3 are drafts, not a frozen or reportable benchmark. V3 is the current diagnostic contract; its gold labels still need owner approval. Prior versions are preserved for comparison.

This suite measures runtime 5a in isolation. It does not measure answer quality, identity verification, permission enforcement, retrieval, or final response generation. Bếp Mây is a replaceable fixture; the parser contract and evaluation procedure are domain-neutral.

## Case contract

Each JSONL row contains:

- `benchmark_version` and `catalog_version`;
- fixed `split` (`dev` or `test`), `paraphrase_family_id`, and `conversation_id` for leakage-safe separation;
- prior `context` turns and current `utterance`;
- `expected`: `decision`, `parse_candidates`, `route_tasks` (possibly empty), top-level `polarity`, `negated_intents`, canonical `references`, `missing_slots`, and `ambiguity_type`. V3 also stores `task_outcomes`, one disposition for each intent/target candidate. Each parse candidate contains `intent_id`, its own `polarity`, `negated_intents`, and normalized `slots` with provenance. Candidate-level negative intents must be included in the top-level `negated_intents`. Summary polarity is `negative` only when there is at least one candidate and every candidate is negative; it is `positive` if any positive candidate exists (including a mixed-polarity request) or no candidate was recognized. Candidates are semantic parses; route tasks are the post-validation plan that may execute later.

Decision labels are `route`, `partial`, `clarify`, `unsupported`, and `no_action`. `route` means every positive task is ready to plan; `partial` means one or more tasks are ready while a sibling needs clarification or has no handler. The runtime response's `tasks` array contains only dispatchable route tasks; the benchmark's `route_tasks` field stores the expected version of that array. `task_outcomes` records a disposition for every parsed intent/target. Neither decision means the caller is authorized or a task has run. Identity and access scope are scored at their own boundary. Multiple candidates/route tasks are one per intent and target. A negative candidate may appear under `parse_candidates` for scoring but must never appear in `tasks`; it receives `no_action` in `task_outcomes`. Required/allowed slot names, types, vocabularies, and ID grammars belong in the versioned route catalog, not in model confidence.

For the Bếp Mây fixture, order IDs use `BM-[0-9]{4}` and invoice IDs use `INV-[0-9]{4}-[0-9]{4}`. An unqualified cancellation in this fixture means `order.cancel`; a missing order ID yields `clarify`. Preserve malformed values in a raw slot for diagnosis; do not silently repair them into valid IDs. A missing or invalid required target yields `clarify`. A recognized intent with no registered handler yields `unsupported`, after required information is present. A solely negated request yields `no_action` and must not dispatch. In a mixed request, each positive candidate is evaluated independently: ready tasks may be returned while missing or unsupported siblings receive their own `clarify`/`unsupported` outcome. Top-level `partial` signals that the caller should handle both the ready tasks and the unresolved outcomes; do not silently drop either. The planner derives mixed-request behavior from task polarity even if the model's summary decision says `no_action`. If a compatible entity is referenced, select the most recently mentioned one, checking the current utterance before prior turns; otherwise clarify. References are canonicalized from the entity slot's provenance, not from a second model-generated map. Same-turn entities have `source=current_turn`; history references have `source=prior_turn_N`. An `unknown` intent candidate may retain detected mention slots for diagnosis, but never creates a route task.

`requested_field` is optional. When the user explicitly names or clearly implies a field, the parser should populate it (`trạng thái` → `status`; delivery wording → `delivery_status`; invoice total wording → `total`). If the user is vague, the system may still plan a lookup; downstream retrieval must only fetch fields allowed for the authenticated actor and needed to answer the request. This field-level policy belongs to the catalog/tool contract for a real domain and must be reviewed before production use.

## Current draft coverage

The v1 pilot has 35 cases, with 6 development and 29 test rows; paraphrase families and conversations do not cross splits. The 22-case v2/v3 diagnostic sets concentrate on negation scope, partial multi-task outcomes, malformed IDs, references, follow-up slot filling, unsupported actions and untrusted prompt text. All versions remain drafts. The v1 test split is not an independent blind test, and v3 uses both dev and test rows for diagnosis rather than held-out reporting. These sets cannot establish stable per-intent accuracy or a low production error rate.

The existing `eval/questions.jsonl` scores final answers. Its four G cases do not measure intent, slot, negation, or reference quality. Do not infer a 5a score from the existing LLM answer experiment.

## Metrics

Report numerator, denominator, benchmark/catalog version, and per-slice results:

1. **Intent:** candidate macro-F1, per-intent precision/recall, confusion matrix.
2. **Slots:** parse-candidate exact match; value-level per-slot precision/recall/F1; exact match for IDs and slot provenance. Report post-validation route-task exact match separately.
   V3 also compares `task_outcomes` per target. A correct `partial` outcome must preserve each ready route and each blocked sibling's clarify/unsupported disposition.
3. **Polarity:** summary polarity accuracy, candidate-level polarity exact match, negated-intent exact match, and contrast-pair consistency.
4. **References:** antecedent accuracy split by unique, missing, and multiple/recent antecedents.
5. **Uncertainty:** `false_dispatch` when expected clarify/unsupported/no_action is routed; `wrong_dispatch` for a route with wrong intent/slot; clarify recall; false clarify on clear supported cases; automatic route coverage. Show false dispatch beside coverage.
6. **Serving:** p50/p95 latency, input/output tokens, API calls per request, retry/timeout/provider-error rates, and throughput at named concurrency levels.

A risk-versus-coverage curve is valid only if the parser exposes a score with a threshold selected on a development split. A model's self-reported confidence or raw embedding similarity is not assumed calibrated.

## Error taxonomy

One primary parser error per failing case: `WRONG_INTENT`, `WRONG_SLOT`, `NEGATION_SCOPE`, `REFERENCE_RESOLUTION`, `SHOULD_CLARIFY_BUT_DISPATCHED`, `CLEAR_BUT_OVER_CLARIFIED`, `UNSUPPORTED_MAPPED_TO_ROUTE`, `MULTI_TASK_DROPPED_OR_MERGED`, `OUTPUT_SCHEMA_FAILURE`, `PROVIDER_FAILURE`.

Log parser output separately from the later authorization and execution decision. A downstream block does not make a parser error correct.

## Run protocol

- Freeze route taxonomy/catalog, owner-approved gold labels, parser prompt/schema, model ID, and benchmark version before the final run. Version changes must retain old artifacts and use a new filename.
- Use the fixed `dev` split only for prompt/schema iteration and the untouched `test` split for pilot reporting; keep `paraphrase_family_id` and whole `conversation_id` together. Do not put held-out utterances or close paraphrases in few-shot examples.
- This pilot has no calibrated score or threshold-selection protocol. If a future parser introduces a route/abstain score, expand `dev` with representative unsupported, no-action, multi-task, and reference cases before choosing an operating point; leave `test` untouched.
- Report raw counts and uncertainty intervals for small slices. Do not claim low failure rates from a handful of cases.
- Have a reviewer other than the parser author approve gold labels. Keep this suite separate from `eval/questions.jsonl`; promotion requires versioning and rerunning comparable prior evaluations.
- Separate deterministic contract/unit tests, semantic benchmark runs, and load tests. They answer different questions.

No reportable 5a parser score exists yet. One live draft-only route smoke case passed after enabling JSON MIME output; it does not estimate accuracy. `score.py` marks draft labels `draft_preview_not_reportable_as_accuracy` and reports raw counts, Wilson intervals for selected rates, group slices, errors, latency, tokens, and retries.

## Owner-readable diagnostic set

`review-v3-diagnostic.md` lists 22 targeted cases in plain language. Its matching JSONL file is intentionally labeled `intent-v3-diagnostic-draft`; it supplements rather than replaces the v1 pilot and preserves v2. It concentrates on negation scope, per-task outcomes for compound requests, malformed IDs, compatible/incompatible references, follow-up slot filling, in-domain unsupported actions, prompt text injection, and self-asserted roles. A task with missing required information gets `clarify`; a task with no handler gets `unsupported`; valid sibling tasks may still appear in dispatchable `tasks`, and the overall plan is `partial`. The execution layer must surface blocked outcomes and must never dispatch those blocked siblings. Run it with explicit paths:

```powershell
uv run python eval/intent/validate.py --gold eval/intent/cases-v3-diagnostic-draft.jsonl --catalog eval/intent/catalog-bm-v1.json
uv run python eval/intent/run.py --gold eval/intent/cases-v3-diagnostic-draft.jsonl --catalog eval/intent/catalog-bm-v1.json --split all --out data/private/intent-v3-diagnostic.jsonl
uv run python eval/intent/score.py --gold eval/intent/cases-v3-diagnostic-draft.jsonl --split all --predictions data/private/intent-v3-diagnostic.jsonl
```

The diagnostic run stays preview-only because its labels are drafts. Use the readable v3 review guide and [v3 run report](reports/diagnostic-v3-2026-11-12.md) for owner review; do not present its aggregate as production accuracy. The v2 guide and report are retained as history.

## Commands

From the repository root:

```powershell
uv run python eval/intent/validate.py
uv run python eval/intent/run.py --split dev --out data/private/intent-v1-dev.jsonl
uv run python eval/intent/score.py --split dev --predictions data/private/intent-v1-dev.jsonl
```

After prompt/catalog changes stop, use a new output filename for each run, compare on `dev`, then run `--split test` once for the candidate. The runner loads the configured model/API key from the local environment; it does not use the final-answer cache. The parser requests JSON MIME output and still validates against the local Pydantic contract. It does not send the dynamic slot map as a provider JSON Schema because Gemini Developer API rejects `additionalProperties`; semantic validation stays in the harness. Results belong under `data/private/` and must not be committed. Draft results are preview-only.
