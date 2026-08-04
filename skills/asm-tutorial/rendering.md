# Phase 3 -- Render

Mechanical, once the markdown from Phase 2 exists:

    <skill-dir>/make_pdf.py <doc.md>

(Run it the way `SKILL.md`'s "Paths used below" section says to -- e.g.
through a project's mandated container wrapper; do not assume a bare
`python3` on the machine running this skill.) This runs pandoc (markdown ->
HTML, `tutorial.css` as the print stylesheet,
`--shift-heading-level-by=-1` so the document's single `#` becomes a title
page instead of the first Contents entry) and then headless Chrome's
`Page.printToPDF` over the DevTools protocol. `<doc>.pdf` lands beside
`<doc>.md`. Pass `--keep-html` to keep the intermediate HTML -- the thing to
look at when the PDF comes out wrong.

## If a code block wraps or a page looks wrong

`tutorial.css`'s code sizing is arithmetic, not a guess, and it is specific to
*this* document's longest line:

    max_line_chars * 0.602 * code_pt <= paper_width_pt - 2 * margin_pt

`0.602` is DejaVu Sans Mono's advance width in em/char -- fixed. `paper_width_pt`
is 612 (US Letter) and `margin_pt` is `MARGIN_X` in `make_pdf.py` (21mm ->
about 59.5pt) -- also fixed, changing them reflows every page. The only
variable is `max_line_chars`: measure the longest line in *this* tutorial's
code blocks (`grep` the markdown, or use `check_pdf.py`'s `code_lines()`) and
solve for `code_pt`. If the current 7.7pt in `tutorial.css`'s `pre` rule
already satisfies the inequality for this document, leave it. If not,
recompute and update the `pre { font-size: ... }` rule, updating the header
comment's arithmetic too so the next reader does not have to redo it from
scratch.

## Why this pipeline and not something simpler

- **Chrome via CDP, not `--print-to-pdf`.** The command-line flag gives no
  control over the header/footer: it either stamps every page with the
  `file://` URL, or (`--print-to-pdf-no-header`) drops page numbers entirely.
  CDP's `Page.printToPDF` takes an explicit `headerTemplate`/`footerTemplate`.
- **A load-wait that polls, not `Page.loadEventFired`.** The event can fire
  before the listener attaches, which cannot be distinguished from "already
  fired" without a race. Polling `Runtime.evaluate` for
  `location.href === <target> && document.readyState === 'complete' &&
  document.fonts.status === 'loaded'` cannot race, because it re-checks
  `location.href` -- that is what tells "our page is done" apart from "the
  about:blank we started on was already done."
- **Ragged right, not justified.** Headless Chrome here has no hyphenation
  dictionary, so `hyphens: auto` is a no-op, and justifying a measure this
  wide around long monospace identifiers opens visible rivers of white space.
- **Liberation Serif for body text, DejaVu Sans Mono for code.** Liberation
  Serif is a Times clone, narrower than DejaVu Serif, which is what makes an
  11pt body tolerable at this measure. Liberation Mono (a Courier clone) is
  too light for dense listings, so code stays DejaVu.

## Requirements

- `pandoc` -- expected to already be in the container image; if missing,
  something else is wrong and this stops with a clear message rather than
  guessing a substitute.
- `google-chrome-stable` (or another binary in `make_pdf.py`'s
  `CHROME_CANDIDATES`) -- installed by hand, does not survive
  `./teardown.sh` or an image upgrade. Reinstall with the project's own
  Chrome-install script if one exists (e.g. `gpu_docker/install-chrome.sh`);
  otherwise download and install `google-chrome-stable` the same way.
- `python3 -c 'import websockets'` -- present via vLLM in images that ship it;
  otherwise `pip install websockets`.
