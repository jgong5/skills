# Phase 4 -- Verify

    <skill-dir>/check_pdf.py <doc.pdf> <doc.md>

(Run it the way `SKILL.md`'s "Paths used below" section says to -- e.g.
through a project's mandated container wrapper.)

## Mechanical checks, over every page

- **Fonts embedded.** `pdffonts <doc.pdf>` -- every row's `emb` column must
  read `yes`. A font pulled from the system rather than embedded will not
  render the same on a machine that lacks it.
- **No wrapped code.** Every non-blank line inside a fenced code block in the
  markdown must appear verbatim, modulo whitespace, somewhere in
  `pdftotext -layout <doc.pdf> -`'s output -- comparing with internal
  whitespace runs collapsed, not just the line's ends stripped, since
  `pdftotext` reconstructs spacing from glyph column positions and commonly
  reflows a right-aligned comment column to a different space count than the
  source even when nothing actually wrapped. A line that genuinely did wrap
  in the rendered PDF comes back as two separate lines and still fails this
  check. This whitespace handling is the mechanical form of the single
  defect class that cost the most time on the first tutorial this skill was
  generalized from -- see `rendering.md`'s note on the code-sizing
  arithmetic if this fires for real.
- **Cross-references resolve.** Every "section N" / "sections N and M" in the
  markdown prose must name a `## N.` heading that actually exists.
- **Page count.** `pdfinfo <doc.pdf>` must report a `Pages:` line.

`check_pdf.py` exits 0 when all four pass, printing a one-line "clean: N
pages, all fonts embedded" summary followed by the sample-page table below --
that summary is success, not a problem to investigate. It exits 1 with one
`PROBLEM:` line per failed category on stderr instead, and skips the
sample-page table.

## Visual, sampled

Six pages regardless of document length, because eyeballing every page of a
long tutorial does not scale and does not need to: title, contents, the page
carrying the widest code block, a table page, a dense prose page, and the
last page. `check_pdf.py` prints the page number for each -- it already has
the extracted text, so it works these out itself; do not hunt for them by
hand. Rasterize the ones it reports with:

    pdftoppm -f <N> -l <N> -png <doc.pdf> page

and look at `page-<N>.png`.

## The failure loop

A finding from either pass goes back to **Phase 2** (the markdown), not Phase 3
(the render command). Classify it first:

- **Content problem** -- a code line is genuinely too long, a cross-reference
  points at a section that got renumbered, a claim in the ledger was
  transcribed wrong. Fix the markdown.
- **Typography problem** -- the stylesheet's arithmetic no longer holds for
  this document's longest line, a table column is too wide, spacing is off.
  Fix `tutorial.css` (see `rendering.md`), not the markdown.

Re-rendering before making this classification just reproduces the same
defect in a fresh PDF. Fix, then re-render, then re-verify.
