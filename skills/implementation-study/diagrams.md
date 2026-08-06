# Diagram language: inline SVG

A study is diagram-first: the figures carry the implementation's shape, and
prose explains the consequence instead of reading every box and arrow aloud.
The figures are still evidence-bearing assertions. Every factual node, edge,
transition, and comparison must be established in the visual inventory or the
decision inventory, then supported by the cited interpretation immediately
after the figure.

Use inline SVG because the deliverable is a printed PDF. Chrome preserves it as
sharp vector paths with selectable text at every zoom, while raw HTML passes
through the existing pandoc pipeline without another renderer or asset file.
Do not use Mermaid, Graphviz, canvas, linked images, or base64 data.

## The three required views

Every study contains exactly one canonical figure for each role:

- `data-diagram="implementation-structure"` -- the entry point, study boundary,
  load-bearing collaborators, persistent state, and important call/dependency
  edges. It is not a directory tree.
- `data-diagram="execution-flow"` -- input to output, including meaningful data
  movement, branches, state transitions, and a failure path when one matters.
  A genuinely linear or stateless implementation gets an honest linear view,
  not an invented state machine.
- `data-diagram="decision-landscape"` -- consequential choices, realistic
  alternatives, the deciding constraint, and the implementation consequence.
  It visualizes the grounded Phase 2 inventory; it never manufactures a choice
  merely to fill the page.

Optional roles are `state-machine`, `data-layout`, `lifecycle`, `concurrency`,
and `algorithm-stages`. Add one when it replaces a paragraph-length enumeration
with a relationship a reader can see. Visual density is the target, not a quota:
a decorative figure that teaches nothing is still a defect.

## Canonical markup

Use raw HTML at column zero. IDs are unique across the document. Captions are
numbered sequentially from 1, and prose references use the exact form
`Figure N`. `check_pdf.py` reads this structure, so do not rename attributes or
substitute an `<img>`.

```html
<figure class="study-diagram" data-diagram="implementation-structure" id="figure-1">
<svg viewBox="0 0 640 220" role="img" aria-labelledby="figure-1-title figure-1-desc">
<title id="figure-1-title">Implementation structure</title>
<desc id="figure-1-desc">The public entry point delegates to the engine, which owns the queue.</desc>
<defs>
  <marker id="figure-1-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" class="diagram-arrow"/>
  </marker>
</defs>
<rect x="20" y="50" width="170" height="64" rx="6" class="diagram-node diagram-entry"/>
<text x="105" y="78" text-anchor="middle" class="diagram-label">public entry</text>
<text x="105" y="97" text-anchor="middle" class="diagram-note">API boundary</text>
<rect x="250" y="50" width="170" height="64" rx="6" class="diagram-node"/>
<text x="335" y="86" text-anchor="middle" class="diagram-label">engine</text>
<line x1="190" y1="82" x2="244" y2="82" class="diagram-edge" marker-end="url(#figure-1-arrow)"/>
<text x="217" y="68" text-anchor="middle" class="diagram-edge-label">calls</text>
<rect x="480" y="50" width="140" height="64" rx="6" class="diagram-node diagram-state"/>
<text x="550" y="78" text-anchor="middle" class="diagram-label">queue</text>
<text x="550" y="97" text-anchor="middle" class="diagram-note">persistent state</text>
<line x1="420" y1="82" x2="474" y2="82" class="diagram-edge" marker-end="url(#figure-1-arrow)"/>
</svg>
<figcaption>Figure 1. Implementation structure</figcaption>
</figure>

Figure 1 shows that the public API is thin while the engine owns the mutable
queue; that ownership is the boundary that later invariants rely on [C1] [C2].
```

The other canonical figures use the same wrapper and metadata, changing only
`data-diagram`, IDs, geometry, labels, and caption:

```html
<figure class="study-diagram" data-diagram="execution-flow" id="figure-2">
<svg viewBox="0 0 640 220" role="img" aria-labelledby="figure-2-title figure-2-desc">
<title id="figure-2-title">Execution and state flow</title>
<desc id="figure-2-desc">Input moves through validation and one queue transition to output.</desc>
<text x="40" y="80" class="diagram-label">input</text>
<text x="260" y="80" class="diagram-label">queue transition</text>
<text x="540" y="80" class="diagram-label">output</text>
</svg>
<figcaption>Figure 2. Execution and state flow</figcaption>
</figure>
```

```html
<figure class="study-diagram" data-diagram="decision-landscape" id="figure-3">
<svg viewBox="0 0 640 240" role="img" aria-labelledby="figure-3-title figure-3-desc">
<title id="figure-3-title">Decision landscape</title>
<desc id="figure-3-desc">The chosen queue and realistic array alternative meet at the ordering constraint.</desc>
<text x="40" y="80" class="diagram-label">chosen: queue</text>
<text x="40" y="160" class="diagram-label">alternative: array</text>
<text x="390" y="120" class="diagram-label">ordering constraint</text>
</svg>
<figcaption>Figure 3. Decision landscape</figcaption>
</figure>
```

## Drawing grammar

- Nodes are rounded `<rect>` elements followed by visible `<text>` labels. Use
  `diagram-entry`, `diagram-state`, `diagram-alternative`, or
  `diagram-emphasis` in addition to `diagram-node` when meaning requires it.
- Edges are `<line>` or `<path>` with `diagram-edge`; important transfers get a
  `diagram-edge-label`. Dashed `diagram-edge diagram-proposed` means an
  alternative or proposed route, not merely visual variety.
- Put the meaning in text and line style as well as color. The PDF must remain
  understandable in grayscale and to a reader who cannot distinguish hues.
- Set a `viewBox`; let CSS fit the figure to the page. Do not set a bitmap-like
  fixed display width or rasterize the SVG.
- Keep labels short and move explanation into the interpretation. If a figure
  approaches 15 nodes, has crossing edges, or needs tiny type, split it by
  concern and connect the two figures in prose.
- Keep one figure on one page. An over-tall figure is a content-composition
  problem: remove incidental nodes or split the view, never shrink every label.
- Each `<svg>` needs `role="img"`, `aria-labelledby`, a nonempty `<title>`, a
  nonempty `<desc>`, and visible `<text>`. These are both accessibility and
  verification anchors.
- Number every `<figcaption>` as `Figure N. Title`, sequentially, and refer to it
  as `Figure N` in adjacent prose.

## Evidence boundary

SVG has no special citation syntax. Do not put ledger IDs inside the drawing as
the sole support for a claim: the evidence checker intentionally reads the
Markdown prose, not SVG semantics. The paragraph immediately after each figure
states the takeaway and cites the ledger entries supporting its important
nodes, edges, transitions, or comparisons. If Phase 1 or Phase 2 did not
establish a relationship, return there or omit it; drawing is not discovery.
