# Intent, slot, and uncertainty evaluation (v1 draft)

**Status:** version 1 draft, not a frozen or measured benchmark. Gold labels still need owner approval. Version 0 is preserved as `cases-v0-draft.jsonl` and `catalog-bm-v0.json`.

This suite measures runtime 5a in isolation. It does not measure answer quality, identity verification, permission enforcement, retrieval, or final response generation. Bếp Mây is a replaceable fixture; the parser contract and evaluation procedure are domain-neutral.

## Case contract

Each JSONL row contains:

- `benchmark_version` and `catalog_version`;
- fixed `split` (`dev` or `test`), `paraphrase_family_id`, and `conversation_id` for leakage-safe separation;
- prior `context` turns and current `utterance`;
- `expected`: `decision`, `parse_candidates`, `route_tasks` (possibly empty), top-level `polarity`, `negated_intents`, `references`, `missing_slots`, and `ambiguity_type`. Each parse candidate contains `intent_id`, its own `polarity`, `negated_intents`, and normalized `slots` with provenance. Candidate-level negative intents must be included in the top-level `negated_intents`. Summary polarity is `negative` only when there is at least one candidate and every candidate is negative; it is `positive` if any positive candidate exists (including a mixed-polarity request) or no candidate was recognized. Candidates are semantic parses; route tasks are the post-validation plan that may execute later.

Decision labels are exactly `route`, `clarify`, `unsupported`, and `no_action`. `route` means a parse can produce one or more candidate route tasks; it does **not** mean the caller is authorized or a task has run. Identity and access scope are scored at their own boundary. Multiple candidates/route tasks are one per intent/target. A negative candidate may appear under `parse_candidates` for scoring but must never appear in `route_tasks`. Required/allowed slot names, types, vocabularies, and ID grammars belong in the versioned route catalog, not in model confidence.

For the Bếp Mây fixture, order IDs use `BM-[0-9]{4}` and invoice IDs use `INV-[0-9]{4}-[0-9]{4}`. An unqualified cancellation in this fixture means `order.cancel`; a missing order ID yields `clarify`. Preserve malformed values in a raw slot for diagnosis; do not silently repair them into valid IDs. A missing or invalid required target yields `clarify`. A recognized intent with no registered handler yields `unsupported`, after required information is present. A solely negated request yields `no_action` and must not dispatch. In a mixed request, negative candidates never become route tasks while positive candidates are evaluated normally. Planning is all-or-nothing: `route_tasks` are emitted only when the overall decision is `route`; clarify, unsupported, and no_action produce no tasks. If a compatible entity is referenced, select the most recently mentioned one; otherwise clarify.

## Current draft coverage

The 35 cases cover paraphrase, nearby intents, slot extraction, missing/invalid IDs, multiple targets/intents, positive/negative contrasts, negation, compatible/incompatible references, code switching, and unsupported domains. The fixed pilot split has 6 development cases and 29 test cases; paraphrase families and conversations do not cross splits. `I-022` and `I-031` reflect the owner decision that a solely negated action is `no_action`: preserve the negative candidate for parser scoring and emit no route task. All rows are still drafts, not accepted gold labels. The owner has seen the v0 suite; this pilot split is not an independent blind test. Dev is too small and lacks key uncertainty slices for threshold selection; test coverage is thin for unsupported in-domain requests, ambiguous intents, mixed valid/invalid multi-task requests, and reference boundary cases. With only 29 held-out cases across many intents, it cannot establish stable per-intent accuracy or a low production error rate.

The existing `eval/questions.jsonl` scores final answers. Its four G cases do not measure intent, slot, negation, or reference quality. Do not infer a 5a score from the existing LLM answer experiment.

## Metrics

Report numerator, denominator, benchmark/catalog version, and per-slice results:

1. **Intent:** candidate macro-F1, per-intent precision/recall, confusion matrix.
2. **Slots:** parse-candidate exact match; value-level per-slot precision/recall/F1; exact match for IDs and slot provenance. Report post-validation route-task exact match separately.
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

## Commands

From the repository root:

```powershell
uv run python eval/intent/validate.py
uv run python eval/intent/run.py --split dev --out data/private/intent-v1-dev.jsonl
uv run python eval/intent/score.py --split dev --predictions data/private/intent-v1-dev.jsonl
```

After prompt/catalog changes stop, use a new output filename for each run, compare on `dev`, then run `--split test` once for the candidate. The runner loads the configured model/API key from the local environment; it does not use the final-answer cache. The parser requests JSON MIME output and still validates against the local Pydantic contract. It does not send the dynamic slot map as a provider JSON Schema because Gemini Developer API rejects `additionalProperties`; semantic validation stays in the harness. Results belong under `data/private/` and must not be committed. Draft results are preview-only.
