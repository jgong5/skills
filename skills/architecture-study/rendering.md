# Phase 5: Render

Phase 5 turns the finished `<stem>_architecture.md` into
`<stem>_architecture.pdf`. "Finished" includes the terminal Evidence ledger
`check_evidence.py materialize-ledger` generated at the end of Phase 4; Render
never copies or edits that chapter.

Nothing here changes what the document says. Phase 5 is mechanical layout: it
exists to catch a document that is content-correct but does not fit the page,
and to fix that without touching the content. If the content is wrong, that is
a Phase 4 problem, and if a claim is wrong it is a Phase 1, 2, or 3 problem.

## Preflight

Render needs pandoc, a Chrome-family binary, and the `websockets` Python
package -- exactly what `<skill-dir>/make_pdf.py` checks at startup and reports
by name when missing. Do not work around a missing dependency by downgrading
the render (dropping `--keep-html`, hand-editing the HTML, skipping fonts):
stop and report the specific gap.

- `pandoc` -- expected to be present already; missing, it is an environment
  problem, not a document problem.
- a Chrome-family binary (`google-chrome`, `google-chrome-stable`, `chromium`,
  or `chromium-browser` -- `make_pdf.py`'s `CHROME_CANDIDATES`). Chrome does
  not survive a container teardown or an image rebuild; if the project
  documents a Chrome-install script, point the user at it by name rather than
  installing a substitute browser.
- `websockets`, imported by `make_pdf.py` to drive Chrome over the DevTools
  protocol; install it the project's usual way if it is absent.

## Classify oversized code before changing styles

Before touching `tutorial.css`, find every code line that is a candidate for
wrapping and every code block tall enough to threaten a page break, and
classify each. Four kinds, and only one is a styling problem:

- **A reducible excerpt.** It is long because it was pasted in full when a
  shorter, still-honest excerpt would carry the same evidence. Trim it in the
  markdown. Preferred whenever honest: it shrinks the widest line without
  touching a font size every other block on the page also lives with.
- **A semantic source line that must remain whole.** The source line itself is
  long -- a signature with several parameters, a long identifier, a format
  string -- and cutting it would misrepresent what the code says. This is the
  only class that justifies changing the code font size.
- **Accidental prose or table width.** Not a code line at all: a table column,
  a long URL, a paragraph running wide on a stray non-breaking space. Fix the
  markdown rather than touching code sizing on a page with no code problem.
- **A page-tall block.** The problem is height, not width. `tutorial.css` sets
  `break-inside: avoid` on `pre`, which Chrome can only honour for a block
  that fits on a page; a taller one is pushed to the next page and broken
  there anyway, leaving a gap behind it. Shrinking the code font is not the
  fix even when it happens to work, because the font size is set by the width
  arithmetic below and re-solving it for height would shrink every other block
  in the document to rescue one. Fix it in the markdown: a shorter excerpt, or
  a deliberate split with a sentence between the halves saying what the split
  skips. A page-tall `pseudocode` block gets the fix the reader wanted anyway
  -- refine a step into its own named block.

Width and height are independent, and finding one tells you nothing about the
other: the block holding the longest line is usually not the tallest block in
the document. Scan for both.

Once a line is confirmed to be the second class, the code font size is
arithmetic, not a guess, and it is specific to *this* document's longest
surviving line. `tutorial.css` states the inequality at the top of the file,
next to the `pre` rule it constrains:

    N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)

`N` is the character count of the longest indivisible code line after
excerpting away everything shortenable; `0.602` is DejaVu Sans Mono's fixed
advance width in em per character; `612` is US Letter's width in points;
`MARGIN_X` is the side margin in inches set in `make_pdf.py` (`21 / 25.4`,
about 0.827in). Changing `MARGIN_X` changes the right-hand side and reflows
every page, not just the one with the long line -- treat a margin change as a
page-layout decision, not a per-document tweak. Solve for `code_pt`, update
the `pre { font-size: ... }` rule and the header comment's copy of the
arithmetic together, and leave the shipped size alone when it already
satisfies the inequality for this document's `N`.

## Classify oversized diagrams before changing styles

Inline SVG is vector content, but a vector is still unreadable with too much
meaning on one page. Inspect every figure for colliding labels, crossing
edges, nodes needing tiny type, or a height that forces a page break. Fix in
the markdown, in this order: shorten labels while preserving meaning, remove
incidental nodes outside the declared boundary, then split the figure by
concern and connect the parts in prose. Never rasterize a figure, scale one
crowded figure until its text is too small, or shrink every diagram to rescue
one bad composition.

`figure.study-diagram` is kept on one page by `tutorial.css`, just as `pre` is,
and that protection only works when the figure fits. An over-tall
`system-decomposition` figure is usually the boundary telling you it is too
wide -- and that is a Phase 1 finding worth acting on, not a CSS problem.

If an SVG looks wrong, render with `--keep-html` and open the intermediate
HTML to separate raw-markup or pandoc behaviour from Chrome print layout
before changing either the source or the CSS.

## Render through the project wrapper

Invoke the renderer through the project's command wrapper, never a bare
`python3`:

    <skill-dir>/make_pdf.py <stem>_architecture.md

`make_pdf.py` runs pandoc (markdown to HTML, `tutorial.css` as the print
stylesheet, `--shift-heading-level-by=-1` so the document's single `#` becomes
a title page rather than the first Contents entry) and then headless Chrome's
`Page.printToPDF` over the DevTools protocol; the PDF lands beside the
markdown. Pass `--keep-html` whenever a render looks wrong -- opening the
intermediate HTML in a browser is the actual diagnosis path, showing whether a
problem is pandoc's HTML generation or Chrome's PDF layout before you spend
another render cycle guessing.

## Inspect the generated artifacts

A clean exit from `make_pdf.py` is necessary, not sufficient. Before treating
Phase 5 as done, confirm:

- the PDF exists, is nonempty, and its size is in the same order of magnitude
  as a comparable report rather than a near-empty file that rendered blank;
- the **Notes** chapter is present at the back, one entry per footnote, and no
  entry is a bare restatement of its own inline expansion. Footnotes land
  there rather than at the foot of the referencing page because Chrome's print
  engine implements no paged-media footnote model -- see the comment in
  `tutorial.css`. This is the layout the document is designed around, not a
  defect to chase;
- if `--keep-html` was used to diagnose something, that the HTML is deleted or
  is clearly a scratch artifact. It is not part of the deliverable.

## Phase 5 exit criteria

Do not move to Phase 6 until all of the following are true:

- every overlong code line has been classified as a reducible excerpt, a
  semantic line that must remain whole, or accidental prose/table width, and
  handled accordingly -- excerpted, sized, or rewrapped, in that order of
  preference;
- every code block taller than a page has been excerpted or split in the
  markdown, never resized;
- every inline-SVG figure fits on one page with readable labels and uncrossed
  edges; crowded figures were simplified or split, never rasterized or
  globally shrunk;
- any `tutorial.css` font-size change is backed by the
  `N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)` arithmetic recomputed for
  this document's actual `N`, with the header comment updated to match;
- `make_pdf.py` ran through the project's command wrapper and exited cleanly;
- the PDF exists, is nonempty, carries a Notes chapter, and any diagnostic
  `--keep-html` output has been cleaned up.
