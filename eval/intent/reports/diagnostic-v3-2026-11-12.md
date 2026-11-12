# Intent v3 diagnostic run — 2026-11-12

## Read this first

This is one exploratory run on 22 **draft** cases, not an approved benchmark or a production accuracy estimate. The run used `gemma-4-31b-it` through Gemini. Two requests failed at the provider boundary; the other 20 returned parser output. The scorer status is `draft_preview_not_reportable_as_accuracy`.

The model calls and timings are in the ignored local artifact `data/private/intent-v3-diagnostic-20261112.jsonl`. A deterministic offline replay then applied the catalog ID grammar normalizer and regenerated route plans from those same model outputs; it did not make additional model calls. Final scorer input: `data/private/intent-v3-diagnostic-20261112-final.jsonl`.

## Results

| Measure | Result |
|---|---:|
| Draft cases | 22 |
| Successful parser responses | 20 |
| Provider failures | 2 (`TransientError`: D-004, D-011) |
| Top-level decisions matching expectation | 20/20 successful responses; 20/22 including provider failures |
| Parse candidate exact match | 20/22 |
| Dispatchable route-task exact match | 20/22 |
| Per-target task-outcome exact match | 20/22 |
| Reference provenance exact match | 22/22 |
| Plan ambiguity / missing-slot exact match | 22/22 |
| False dispatch / wrong dispatch | 0 / 0 |
| Candidate polarity / negated-intent exact match | 20/22 / 21/22 |

The two semantic decision/task misses are provider failures, not incorrect parser decisions. D-010's mixed request behaved as designed: the complete order lookup was routed while the invoice task was marked `clarify` for its missing invoice ID. D-011, which probes a supported lookup beside a handlerless cancellation, could not be evaluated because of a provider failure.

Compared with v2, the prompt now directly names common field mappings, the planner emits a decision per intent/target, references are scored from canonical slot provenance, and valid IDs emitted in both normalized and `_raw` slots are deduplicated deterministically. In this one run, all 20 successful parse candidates matched after normalization. This comparison is diagnostic only: each version has one small run and provider conditions vary.

## Serving observations

| Measure | This sequential run |
|---|---:|
| Model latency p50 / p95 | 37.81 s / 55.52 s |
| Parse latency p50 / p95 | 51.52 s / 102.90 s |
| Input / output tokens | 32,378 / 12,035 |
| Retries | 20 |
| Provider errors | 2/22 |

These measurements describe one sequential run only. They do not establish stable service reliability, concurrent throughput, or production cost.

## Decisions implemented

1. `requested_field` remains optional in the fixture. The parser is instructed to fill it when the utterance names or clearly implies the field; a vague request does not get a guessed field.
2. Each positive intent/target receives its own outcome. Ready siblings may appear in `tasks`; a missing sibling is `clarify`, and a task without a handler is `unsupported`. The top-level plan uses `partial`. Only `tasks` may be passed to later execution, and every blocked sibling must be surfaced to the user.
3. Reference correctness comes from the target slot and its provenance (`current_turn` or `prior_turn_N`). A model-generated duplicate reference map is ignored; the route planner returns the canonical map.
4. The planner derives mixed-request behavior from per-task polarity, even if the model's global summary says `no_action`; an all-negative request still returns `no_action`.

These choices implement Tier 1–2 planning only. No tool, retrieval, or protected-data action is run here.

## Remaining gate

The v3 cases remain draft labels. An independent reviewer found the labels internally consistent, but owner gold approval and a future held-out score remain open. This set combines dev and test cases and is used only for diagnosis. Live Keycloak, semantic input-safety policy, ACL filtering, and tool execution are also separate gates.
