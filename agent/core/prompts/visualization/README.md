# Backend visualization resources

`read_module_guideline(modules) -> str` remains the agent tool. `shared.jinja2`
is rendered once, followed by unique module guides and unique templates in request
order. `MODULE_TEMPLATES` in `agent/core/tools/visualize.py` declares composition.
Composable snippets in `templates/` intentionally use the `.html` extension because
they are HTML fragments rendered directly inside visualization fences; the Jinja
loader resolves that extension explicitly.
The five fence names remain interactive, chart, diagram, mockup, and art. A dashboard
combines templates in an interactive fence; it does not introduce another agent or
module. This directory replaces the old core includes and unused tool README prompt.

## Host contract (frontend integration deferred)

A host must install `assets/lavish.css`, load global `Chart` and global `mermaid`,
and execute `assets/preview-bootstrap.js` **before** executing fragment scripts.
The standalone exporter in `preview.py` pins Chart.js **4.4.8** and Mermaid **11.4.1**
with blocking classic script tags in that order. It then embeds the bootstrap and
fragment. No frontend imports, runtime helpers, Tailwind, DaisyUI, remote fonts, or
Lavish editor server are required. CDN access is required for chart/diagram previews;
HTML, local styles, controls and SVG remain self-contained. These are standalone
files with remote library dependencies, not fully offline bundles.

Bootstrap sets chart defaults and initializes Mermaid with `startOnLoad: false`,
strict security, and the fixed dark Lavish palette. Generated scripts call
`new Chart(...)` and `await mermaid.run({nodes: [...]})` directly, after their DOM.
They own control behavior and use unique IDs and scoped selectors. Each fragment is
independent. The host owns library/style loading; it must not re-execute scripts
while a fragment is incomplete. A later frontend integration must supply this same
contract and handle its own mounting, resizing and cleanup. The existing frontend,
iframe styles, streaming parser and runtime assets are unchanged in this phase.

`lv-panel`, `lv-card`, `lv-grid`, `lv-stack`, `lv-row`, `lv-button`, `lv-input`,
`lv-label`, `lv-toggle`, `lv-pill`, `lv-eyebrow`, `lv-value`, `lv-muted`, and
`lv-chart` are the available CSS classes. `--lv-*` tokens provide background, panel,
elevated surface, foreground, muted text, border, accent, danger and font families.
Controls use native HTML semantics; generated scripts supply their behavior.

## Provenance

Adapted from [kunchenguid/lavish-axi](https://github.com/kunchenguid/lavish-axi),
commit **50b0facb61b5fc36cb1737e33b20d2894a64323b**, inspected from the local checkout:

- [src/chrome.css](https://github.com/kunchenguid/lavish-axi/blob/50b0facb61b5fc36cb1737e33b20d2894a64323b/src/chrome.css): ink/steel/cream/brass tokens, serif/sans/mono typography, panel surfaces, cards, buttons, inputs and pill treatment.
- [src/design-reference.js](https://github.com/kunchenguid/lavish-axi/blob/50b0facb61b5fc36cb1737e33b20d2894a64323b/src/design-reference.js): portable HTML, responsive layout safeguards, form/toggle semantics, and direct Mermaid initialization.

This is a small plain HTML/CSS/JS adaptation, not a copy of the editor chrome or
its DaisyUI/Tailwind runtime. The CSS retains the upstream MIT license notice,
including in exported previews. Toggles are native checkboxes restyled with the
same tokens. System font fallbacks avoid a font-loading dependency.

API references: [Chart.js script integration](https://www.chartjs.org/docs/latest/getting-started/integration.html)
and [Mermaid usage](https://mermaid.js.org/config/usage.html).

See [local sample commands](../../../../local/VISUALIZE.md) for generation and review.
