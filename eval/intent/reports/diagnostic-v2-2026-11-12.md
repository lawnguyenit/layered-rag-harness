# Intent v2 diagnostic run — 2026-11-12

## Read this first

This is one exploratory run against 22 **draft** cases, not an approved benchmark and not a production accuracy estimate. The set mixes development and test rows and is intentionally used to find defects. The provider was `gemma-4-31b-it` through Gemini. Raw per-case output stays in ignored `data/private/intent-v2-diagnostic-20261112.jsonl`.

## What happened

- All 18 requests that returned a parse produced the expected top-level decision (18/18). The scorer counts the four provider failures as incorrect, so its draft-preview decision count is 18/22.
- All returned decisions for pure negation, mixed negation, self-correction, unsupported intents, and the prompt-injection-like example matched the draft expectations. No expected blocked case was routed (`false_dispatch = 0` in this small set).
- Four requests failed before semantic scoring: three `TransientError` (D-007, D-011, D-012) and one `EmptyResponse` (D-015). These represent a 4/22 request failure rate in this single run; repeat runs are needed before treating it as a stable serving rate.
- Exact parse-candidate slot match was 10/22. The recurring semantic gap was omission of the optional `requested_field` (for example, `status` or `delivery_status`) even when the intent and order ID were right. This field is not required by the current route catalog, so the harness can route without it; the draft benchmark nevertheless expects it. Decide whether it is a required downstream contract field or an optional answer preference, then align catalog and gold labels.
- Reference behavior needs a metric-contract cleanup. D-018 had the right `order_id` and `source=prior_turn_2` in its parsed task, but the parser did not emit the gold's canonical `references.order_id` entry; the deterministic planner populated it. D-014 similarly resolved the order ID, while the parser used a surface-phrase-to-ID map. The strict raw-map comparison therefore reports a reference mismatch even when the route slot is correct. Score canonical slot provenance at the parser boundary, or specify and enforce one canonical `references` schema.
- D-010 matched the temporary all-or-nothing expectation. D-011, the second compound-policy probe, failed at the provider, so it remains untested. The policy is still for the owner to decide; these two rows are not approved gold.

## Serving observations

| Measure | This run |
|---|---:|
| Requests | 22 |
| Provider failures | 4 (3 transient, 1 empty response) |
| Parse latency p50 / p95 | 38.35 s / 92.67 s |
| Model latency p50 / p95 | 33.58 s / 46.86 s |
| Input / output tokens | 27,593 / 9,058 |
| Retries | 11 |

These are observations for one sequential run on the configured Gemini service. They do not predict concurrent throughput, stable latency, or per-user cost.

## Decisions still needed

1. Should `requested_field` be required for an `order.lookup` route, or may the later retrieval/answer layer infer a default?
2. For a compound request with a valid task and a missing or unsupported sibling, should the harness block the whole request or allow partial planning? D-010/D-011 only probe a provisional all-or-nothing assumption.
3. Should parser references be scored from the canonical slot's `source`, or should the model be required to populate a separately defined `references` map?

## Evidence and limits

- Independent review found the 22 JSONL rows consistent with their readable guide and documented conventions.
- Independent verification after the same-turn reference fix: 74 tests passed, 2 skipped; validators accepted v2/v1/v0 (22/35/30 cases). One Starlette `httpx`/`TestClient` deprecation warning remains.
- The local deterministic planner now prefers compatible IDs in the current utterance before prior turns, and only records prior-turn entities in its cross-turn `references` map. This does not establish model semantic accuracy.
- Scorer output remains `draft_preview_not_reportable_as_accuracy`. The live Keycloak check, semantic safety policy, owner-approved gold, and held-out semantic benchmark remain open.
