# Diagram language: inline SVG

The report is diagram-first: the figures carry the system's shape and the
prose carries the consequence, rather than reading every box and arrow aloud.
Figures are still evidence-bearing assertions. Every node, edge, transition,
and comparison must come from an inventory Phases 1 to 3 built, and the
paragraph immediately after the figure states the takeaway with its ledger
IDs.

Use inline SVG because the deliverable is a printed PDF. Chrome preserves it
as sharp vector paths with selectable text at every zoom, and raw HTML passes
through the existing pandoc pipeline without another renderer or an asset
file. Do not use Mermaid, Graphviz, canvas, linked images, or base64 data.

## The four required views

Exactly one canonical figure for each role:

- `data-diagram="system-decomposition"` -- the components inside the boundary,
  what each owns, the dependency and call edges between them, and the boundary
  edges drawn as the edges they are. Mark the paradigm per layer where the
  layers are visible. It is not a directory tree, and a directory tree drawn
  as boxes is the most common way this figure says nothing.
- `data-diagram="contract-map"` -- the seams, and what crosses each one.
  Label edges with the shape that travels (`RequestBatch`, `fp16 [B,S,H]`,
  `LoweredGraph`), not with a verb. Where ownership transfers, say so on the
  edge. This is the figure a reader uses to decide whether they could replace
  a component, so a seam that does not cut should look different from one that
  does.
- `data-diagram="execution-lifecycle"` -- the traced loop from entry to exit,
  with the state mutations, allocations, seam crossings, waits, and at least
  one failure path. A genuinely linear path gets an honest linear view, not an
  invented state machine.
- `data-diagram="tradeoff-landscape"` -- the decisions from Phase 3, their
  realistic alternatives, the deciding constraint where they meet, and the
  consequence. It visualises the grounded inventory; it never manufactures a
  choice to fill the page.

Optional roles are `blocking-path`, `alternative-paradigm`, `state-machine`,
`data-layout`, `memory-lifetime`, `concurrency`, and `failure-modes`. Sections
5 and 6 usually earn the first two. Add one when it replaces a
paragraph-length enumeration with a relationship a reader can see. Visual
density is the target, not a quota: a decorative figure that teaches nothing
is still a defect.

## Canonical markup

Raw HTML at column zero. IDs are unique across the document, captions are
numbered sequentially from 1, and prose references use the exact form
`Figure N`. `check_pdf.py` reads this structure, so do not rename attributes
or substitute an `<img>`.

```html
<figure class="study-diagram" data-diagram="system-decomposition" id="figure-1">
<svg viewBox="0 0 640 240" role="img" aria-labelledby="figure-1-title figure-1-desc">
<title id="figure-1-title">System decomposition</title>
<desc id="figure-1-desc">The gateway hands requests to the scheduler, which owns the batch state and drives a stateless executor.</desc>
<defs>
  <marker id="figure-1-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" class="diagram-arrow"/>
  </marker>
</defs>
<rect x="20" y="60" width="160" height="64" rx="6" class="diagram-node diagram-entry"/>
<text x="100" y="88" text-anchor="middle" class="diagram-label">gateway</text>
<text x="100" y="107" text-anchor="middle" class="diagram-note">reactor</text>
<rect x="240" y="60" width="160" height="64" rx="6" class="diagram-node diagram-state"/>
<text x="320" y="88" text-anchor="middle" class="diagram-label">scheduler</text>
<text x="320" y="107" text-anchor="middle" class="diagram-note">owns batch state</text>
<rect x="460" y="60" width="160" height="64" rx="6" class="diagram-node"/>
<text x="540" y="88" text-anchor="middle" class="diagram-label">executor</text>
<text x="540" y="107" text-anchor="middle" class="diagram-note">stateless</text>
<line x1="180" y1="92" x2="234" y2="92" class="diagram-edge" marker-end="url(#figure-1-arrow)"/>
<text x="207" y="78" text-anchor="middle" class="diagram-edge-label">Request</text>
<line x1="400" y1="92" x2="454" y2="92" class="diagram-edge" marker-end="url(#figure-1-arrow)"/>
<text x="427" y="78" text-anchor="middle" class="diagram-edge-label">Batch</text>
</svg>
<figcaption>Figure 1. System decomposition</figcaption>
</figure>

Figure 1 shows the batch state living in exactly one component: the executor
is handed a batch and keeps nothing, which is why a failed step can be retried
without unwinding anything outside the scheduler [C2][K5].
```

The other three use the same wrapper and metadata, changing only
`data-diagram`, IDs, geometry, labels, and caption:

```html
<figure class="study-diagram" data-diagram="contract-map" id="figure-2">
<svg viewBox="0 0 640 220" role="img" aria-labelledby="figure-2-title figure-2-desc">
<title id="figure-2-title">Contract map</title>
<desc id="figure-2-desc">Two seams cut cleanly; the executor seam leaks a warmup ordering requirement.</desc>
<text x="60" y="80" class="diagram-label">gateway seam</text>
<text x="300" y="80" class="diagram-label">RequestBatch, owned by callee</text>
<text x="60" y="160" class="diagram-label">executor seam</text>
<text x="300" y="160" class="diagram-label">leaks: warmup() must precede</text>
</svg>
<figcaption>Figure 2. Contract map</figcaption>
</figure>
```

```html
<figure class="study-diagram" data-diagram="execution-lifecycle" id="figure-3">
<svg viewBox="0 0 640 220" role="img" aria-labelledby="figure-3-title figure-3-desc">
<title id="figure-3-title">Execution lifecycle</title>
<desc id="figure-3-desc">One request from admission through one batched step to release, with the timeout path.</desc>
<text x="40" y="80" class="diagram-label">admit</text>
<text x="240" y="80" class="diagram-label">batch step</text>
<text x="460" y="80" class="diagram-label">release</text>
<text x="240" y="170" class="diagram-label">timeout: evict, free KV block</text>
</svg>
<figcaption>Figure 3. Execution lifecycle</figcaption>
</figure>
```

```html
<figure class="study-diagram" data-diagram="tradeoff-landscape" id="figure-4">
<svg viewBox="0 0 640 240" role="img" aria-labelledby="figure-4-title figure-4-desc">
<title id="figure-4-title">Trade-off landscape</title>
<desc id="figure-4-desc">Paged blocks and a contiguous arena meet at the fragmentation constraint.</desc>
<text x="40" y="80" class="diagram-label">chosen: paged blocks</text>
<text x="40" y="170" class="diagram-label">alternative: contiguous arena</text>
<text x="380" y="125" class="diagram-label">deciding: fragmentation</text>
</svg>
<figcaption>Figure 4. Trade-off landscape</figcaption>
</figure>
```

## Drawing grammar

- Nodes are rounded `<rect>` elements followed by visible `<text>` labels. Add
  `diagram-entry`, `diagram-state`, `diagram-alternative`, or
  `diagram-emphasis` to `diagram-node` when meaning requires it. Use
  `diagram-state` for a component that owns mutable state and plain
  `diagram-node` for one that does not -- ownership is the single most useful
  thing these figures can encode.
- Edges are `<line>` or `<path>` with `diagram-edge`; label the important ones
  with `diagram-edge-label`. Dashed `diagram-edge diagram-proposed` means an
  alternative or proposed route, not visual variety.
- Put the meaning in text and line style as well as colour. The PDF must stay
  understandable in grayscale and to a reader who cannot distinguish hues.
- Set a `viewBox` and let CSS fit the figure to the page. Do not set a
  bitmap-like fixed display width or rasterize the SVG.
- Keep labels short and move explanation into the interpretation. If a figure
  approaches 15 nodes, has crossing edges, or needs tiny type, split it by
  concern and connect the parts in prose. A system-decomposition figure that
  will not fit under 15 nodes is usually telling you the boundary is too wide.
- Keep one figure on one page. An over-tall figure is a composition problem:
  remove incidental nodes or split the view, never shrink every label.
- Each `<svg>` needs `role="img"`, `aria-labelledby`, a nonempty `<title>`, a
  nonempty `<desc>`, and visible `<text>`. These are accessibility and
  verification anchors both.
- Number every `<figcaption>` as `Figure N. Title`, sequentially, and refer to
  it as `Figure N` in adjacent prose.

## Evidence boundary

SVG has no citation syntax, and the evidence checker deliberately reads the
Markdown prose rather than SVG semantics. Do not put ledger IDs inside a
drawing as the sole support for a claim. The paragraph immediately after each
figure states the takeaway and cites the entries supporting its important
nodes, edges, and comparisons. If no inventory established a relationship, go
back or leave it out -- drawing is not discovery.

Abbreviations inside SVG text are exempt from the expansion rule in
`<skill-dir>/writing.md`, because a figure label has no room for a
parenthetical. That exemption is a reason to introduce a term in prose
*before* the figure that uses it, not a licence to put an unexplained acronym
on a diagram.
