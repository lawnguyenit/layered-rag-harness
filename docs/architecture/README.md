# Interactive harness flow

This is a dependency-free static architecture viewer for the request lifecycle. The main view is a box-and-arrow data-flow diagram: it follows corpus documents through the planned indexing path, then follows a request through the implemented runtime Tier 1–2 boundary and the planned retrieval, prompt, and model path. The runtime API currently returns a route plan; it does not continue into retrieval or answer generation.

`flow.svg` is the source diagram, mirrored inline in `index.html` for interactive highlighting. Solid arrows carry data, dashed arrows carry configuration or control, and coral branches stop or divert requests. Node labels distinguish code with contract tests from live integration and target-design work. The trace view includes the current G0 answer path as well as target-design examples.

## Real host traces

The "Thật" scenarios in the trace toolbar come from `host-traces.js`, written by `scripts/record_host_traces.py` from real HTTP requests to the host (Keycloak token, PostgreSQL row-level security). It is a snapshot taken at the time shown in the file, not a live feed; rerun the script to refresh it. These traces call the host directly and do not pass through the harness.

## Preview locally

Open `index.html` directly in a browser, or serve the repository root with any static file server and visit `/docs/architecture/`.

## Publish later

The page uses relative links and has no build step. It can be published as a subpath on GitHub Pages (for example, `/docs/architecture/`) or copied to another static host. Hosting and deployment are not configured by this page.

## Keep it accurate

- Use `docs/GATES.md` and source evidence for implementation status; passing contract tests do not imply live provider integration or measured semantic accuracy.
- Keep the runtime route-plan endpoint distinct from the older CLI path that calls Gemini and produces an answer.
- Keep security boundaries consistent with `docs/DATA-CONTRACT.md`.
- Add a dated entry to `docs/PROCESS-LOG.md` when the design changes.
