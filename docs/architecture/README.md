# Interactive harness flow

This is a dependency-free static architecture viewer for the request lifecycle. The main view is a box-and-arrow data-flow diagram: it follows corpus documents through indexing, then follows a live request through identity, routing, access filtering, prompt assembly, and the model boundary. It distinguishes the proposed target design from the code currently implemented in the repository.

`flow.svg` is the source diagram. Solid arrows carry data, dashed arrows carry configuration or control, and coral branches stop requests before restricted text can enter the prompt. Each stage is labeled as current, planned, or proposed. The trace view includes the current G0 path as well as target-design examples.

## Preview locally

Open `index.html` directly in a browser, or serve the repository root with any static file server and visit `/docs/architecture/`.

## Publish later

The page uses relative links and has no build step. It can be published as a subpath on GitHub Pages (for example, `/docs/architecture/`) or copied to another static host. Hosting and deployment are not configured by this page.

## Keep it accurate

- The flow is a design specification, not implementation evidence.
- Update stage labels only when `docs/GATES.md` and source evidence support the change.
- Keep security boundaries consistent with `docs/DATA-CONTRACT.md`.
- Add a dated entry to `docs/PROCESS-LOG.md` when the design changes.
