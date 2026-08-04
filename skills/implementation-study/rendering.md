# Phase 4: Render

Phase 4 turns the finished `<stem>_study.md` from Phase 3 into
`<stem>_study.pdf`. Nothing here changes what the document says -- Phase 4 is
mechanical layout, not a second editing pass. If the content is wrong,
that is a Phase 3 problem (or, if a claim itself is wrong, a Phase 1 or
Phase 2 problem); Phase 4 exists to catch a document that is content-correct
but does not fit the page, and to fix that without touching the content.

## Preflight

Render needs pandoc, a Chrome-family binary, and the `websockets` Python
package, exactly what `<skill-dir>/make_pdf.py` checks for at startup and
reports by name when missing. Do not work around a missing dependency by
downgrading the render (dropping `--keep-html`, hand-editing the HTML,
skipping fonts): stop and report the specific gap instead.

- `pandoc` -- expected to already be present; if it is missing, something is
  wrong with the environment, not with this document.
- a Chrome-family binary (`google-chrome`, `google-chrome-stable`,
  `chromium`, or `chromium-browser` -- `make_pdf.py`'s `CHROME_CANDIDATES`).
  Chrome does not survive a container teardown or an image upgrade; if the
  project documents a Chrome-install script (e.g.
  `gpu_docker/install-chrome.sh`), point the user at it by name rather than
  installing a substitute browser yourself.
- `websockets`, imported by `make_pdf.py` to drive Chrome over the DevTools
  protocol; install it the project's usual way if it is absent.

## Classify wide code before changing styles

Before touching `tutorial.css`, find every code line in `<stem>_study.md`
that is a candidate for wrapping in the rendered PDF and classify each one.
There are three kinds, and only one of them is a styling problem:

- **A reducible excerpt.** The line is long because it was pasted in full
  when a shorter, still-honest excerpt would carry the same evidence --
  trim it in the markdown. This is the preferred fix whenever it is honest:
  it shrinks the widest line without touching the font size that every other
  code block on the page also has to live with.
- **A semantic source line that must remain whole.** The line is long
  because the source itself is long -- a signature with several parameters,
  a long identifier, a format string -- and cutting it would misrepresent
  what the code actually says. This is the only class that justifies
  changing the code font size; see the arithmetic below.
- **Accidental prose or table width.** The overlong line is not a code line
  at all -- a table column, a long URL, or a paragraph that runs wide because
  of a stray non-breaking space or an un-wrapped sentence. Fix the markdown
  (rewrap the prose, narrow the table, shorten the URL) rather than touching
  code sizing for a page that has no code problem.

A render finding is not yet a prose or CSS fix: classify it first, and only
change `tutorial.css` for the second class. Shrinking the font because it is
the fastest fix, without doing this classification, is exactly how a
document accumulates a code size no line on the page actually needed.

Once a line is confirmed to belong to the second class, the code font size
is arithmetic, not a guess, and it is specific to *this* document's longest
surviving line. `tutorial.css` states the inequality at the top of the file,
next to the `pre` rule it constrains:

    N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)

`N` is the character count of the longest indivisible code line in this
document (after excerpting away everything that could be shortened);
`0.602` is DejaVu Sans Mono's fixed advance width in em per character; `612`
is US Letter's width in points; `MARGIN_X` is the side margin, in inches, set
in `make_pdf.py` (`21 / 25.4`, about 0.827in) -- changing `MARGIN_X` changes
the right-hand side of this inequality and reflows every page, not just the
one with the long line, so treat a margin change as a page-layout decision,
not a per-document tweak. Solve for `code_pt` and update `tutorial.css`'s
`pre { font-size: ... }` rule together with the header comment's own copy of
this arithmetic, so the next reader does not have to redo the derivation
from scratch. If the shipped size already satisfies the inequality for this
document's `N`, leave it; a document with no unusually long code needs no
change at all.

## Render through the project wrapper

Invoke the renderer through the project's command wrapper, never a bare
`python3`:

    <skill-dir>/make_pdf.py <stem>_study.md

`make_pdf.py` runs pandoc (markdown to HTML, `tutorial.css` as the print
stylesheet, `--shift-heading-level-by=-1` so the document's single `#`
becomes a title page rather than the first Contents entry) and then headless
Chrome's `Page.printToPDF` over the DevTools protocol; `<stem>_study.pdf`
lands beside `<stem>_study.md`. Pass `--keep-html` whenever a render looks
wrong -- it leaves the intermediate HTML beside the markdown, which is the
actual diagnosis path: opening it in a browser shows whether a problem is
pandoc's HTML generation or Chrome's PDF layout, before spending another
render cycle guessing.

## Inspect the generated artifacts

A clean exit from `make_pdf.py` is necessary, not sufficient. Before treating
Phase 4 as done, confirm:

- the PDF exists and is nonempty, and its size is in the same order of
  magnitude as a comparable study, not a near-empty file that silently
  rendered a blank page;
- if `--keep-html` was used to diagnose a problem, that the HTML is either
  deleted afterward or clearly a scratch artifact -- it is not part of the
  study's deliverable output.

Phase 5 is where the PDF is actually checked against the markdown
mechanically and by eye; Phase 4's own job ends at producing a PDF that is
worth running those checks against.

## Phase 4 exit criteria

Do not move to Phase 5 until all of the following are true:

- every overlong code line has been classified as a reducible excerpt, a
  semantic line that must remain whole, or accidental prose/table width, and
  handled accordingly -- excerpted, sized, or rewrapped, in that order of
  preference;
- any `tutorial.css` font-size change is backed by the
  `N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)` arithmetic, recomputed
  for this document's actual `N`, with the header comment updated to match;
- `make_pdf.py` was run through the project's command wrapper, not a bare
  interpreter, and exited cleanly;
- `<stem>_study.pdf` exists, is nonempty, and any diagnostic `--keep-html`
  output has been cleaned up or is clearly scratch.

A render that "looks fine" without this checklist is not yet verified --
Phase 5 does that mechanically, but Phase 4 should not hand it a document
whose wide lines were never actually classified.
