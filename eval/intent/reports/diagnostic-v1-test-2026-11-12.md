# v1 test split: live draft diagnostic

Run date: 2026-11-12. Model: `gemma-4-31b-it`; provider: Gemini API. Benchmark: `intent-v1-draft`; catalog: `bm-fixture-v1`; split: 29 `test` cases. The run used synthetic draft cases and a draft label set that was not blind or independently approved. **The figures below are diagnostic preview results, not benchmark accuracy or a production quality claim.**

## What the run shows

| Measurement | Result |
|---|---:|
| Parse / plan responses available | 27 / 29 |
| Exact final decision | 27 / 29 |
| Exact final decision, given a plan | 27 / 27 |
| Exact intent candidates, end-to-end / given a parse | 27 / 29; 27 / 27 |
| Intent F1 micro / macro, given a parse | 1.000 / 1.000 (33 TP; 0 FP/FN) |
| Exact slot candidates | 25 / 29 |
| Exact slot candidates, given a parse | 25 / 27 |
| Slot value F1 micro, all cases / given a parse | 0.926 / 0.980 (all cases: 50 TP, 0 FP, 8 FN; conditional macro F1: 0.981) |
| Slot value F1 macro, all cases / given a parse | 0.904 / 0.981 |
| Exact route task list, end-to-end / given a plan | 26 / 29; 26 / 27 |
| Clarify cases returned as clarify, end-to-end / given a plan | 6 / 7; 6 / 6 |
| False dispatch to route/partial on a gold non-route case | 0 / 29 |
| Route-task mismatches on expected route cases | 1 |
| Route coverage | 16 / 29 (55.2%) |
| Polarity summary / reference map exact, end-to-end / available output | 27 / 29 each; 27 / 27 each |
| Negation summary exact, end-to-end / parsed output | 27 / 29; 27 / 27 |
| Parser ambiguity exact, end-to-end / given parse | 20 / 29; 20 / 27 |
| Plan ambiguity and missing-slot exact, end-to-end / available plan or parse | 27 / 29; 27 / 27 each |
| Provider failures | 2 / 29 (`TransientError`) |
| Retries recorded / provider calls with response metadata | 23 / 27 |
| Parse latency p50 / p95 | 49.6 s / 121.4 s |
| Model latency p50 / p95 | 38.8 s / 62.5 s |
| Prompt / output tokens recorded | 44,122 / 14,739 |

At this sample size, 0 observed false dispatches still has a 95% Wilson upper bound of 11.7%. It is evidence for these few cases only, not proof that harmful or ambiguous requests will never dispatch.

## Cases to inspect

- **I-017, I-033 — provider availability:** Two transient provider failures prevented a parse. They count as unsuccessful end-to-end decisions, not parser semantic mistakes.
- **I-021 — negated status plus unsupported cancellation:** The final plan was `unsupported` with no route tasks, so the system did not dispatch either action. The parsed candidate/slot details did not exactly match the draft label; inspect the per-case output before judging whether that label reflects the desired decomposition.
- **I-028 — compound delivery fee and schedule:** The planner preserved two tasks and the right intent/fields, but the fee task omitted `order_total=400000`; exact route-task matching therefore failed. This can affect fee lookup precision.

There were no output-schema failures, timeouts, rate-limited requests, false clarifications, or observed false dispatches in this run. Two scorer defects were corrected after independent review: provider failures no longer get semantic error labels, and unavailable parse/plan outputs cannot earn exact-match credit for empty/default fields. End-to-end metrics count unavailable responses as misses; conditional metrics show quality among the 27 completed responses.

The two failed provider rows have `call=null`; therefore the 23 retries and latency/token totals are only what was recorded for 27 returned metadata rows. They are not complete totals for all attempts.

## Interpretation limits

- The `test` split was seen during development and has draft labels; it is not a held-out gold benchmark.
- Each group is very small, often one or two examples. Per-group percentages are not stable estimates.
- `task_outcome_exact` is not measured here because v1 has no per-task outcome labels.
- The 55.2% route coverage reflects the fixture's mix of route, clarify, unsupported and no-action cases; it is not a service-level coverage target.
- This evaluates intent and route planning only. It does not test document retrieval, authorization enforcement against stored data, tool execution, or answer quality.
- Latency is high and includes sequential live API behavior/retries. Do not use it as a production SLO or compare it with another model without a controlled repeated run.

Human-readable case list: `eval/intent/review-v1-test-draft.md`. Raw request/response metadata and detailed scorer output remain in ignored `data/private/` artifacts and are not committed.
