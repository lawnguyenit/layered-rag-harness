# layered-rag-harness

A learning-and-portfolio project: a document Q&A assistant (RAG) with access control and tool calling, built one layer at a time. After each layer, the same fixed question set is re-run, so every layer has to show which failure it fixes.

**Status:** planning. No code yet (stage 0 not started). See `docs/PLAN.md`.

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
