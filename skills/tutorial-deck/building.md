# Phase 4: Build

Phase 4 turns the confirmed `outline.md` into `build.js`, runs it, and
produces `<stem>.pptx`. Every deckkit warning is fixed before Phase 5
renders anything: a warning is a fault the build already found, and handing
it to a reviewer spends a review round on what a rebuild would have caught.

## Install pptxgenjs in the deck directory

`deckkit.js` drives `pptxgenjs`, but does not ship it. Each deck installs
the version `deckkit.js` pins as `PPTXGENJS_VERSION`, into its own output
directory:

    npm install --no-save --no-package-lock --prefix <out> pptxgenjs@<PPTXGENJS_VERSION>

The install is per deck and pinned because the deck's layout depends on it:
a different `pptxgenjs` can size text boxes and tables differently, and a
deck rebuilt later must come out as it was reviewed. The output directory is
the only place the run may write -- the repository is read-only and the
skill directory belongs to the plugin -- so that is where `node_modules`
goes. `deckkit.js` resolves `pptxgenjs` from the directory of the script that
requires it, not from its own, which is what makes this layout work.

When Node or npm is missing, or the install fails, **stop** and report it.
There is no fallback renderer: a deck built by anything else has none of the
build-time checks this phase depends on.

## Write `build.js`

`build.js` lives in the output directory and requires deckkit by the skill
directory's absolute path, `<skill-dir>/deckkit.js`. If the project's
command wrapper cannot reach `<skill-dir>` (a container mount boundary),
copy `<skill-dir>/deckkit.js` into the output directory and require the
copy instead, `require('./deckkit.js')`: it is the only file from the skill
directory that a command loads, and it still finds `pptxgenjs` in the
output directory's `node_modules`. The header comment of `deckkit.js` shows
the calls; read it rather than a copy here.

- `deck()` takes the title, the pin from `survey.md` as `pin` (printed in
  every footer), `plan.md`'s length as `minutes`, and `plan.md`'s fonts.
- One `slide()` per outline line, in outline order, with the outline's
  title. `section()` before each part of the talk, and `agenda()` for the
  agenda slide, whose rows deckkit fills from the slides' `min`.
- Code goes through `code()` with `cite: 'path: symbol'` and, where the
  slide points at specific lines, `hl`. The excerpt is verbatim from the
  pinned commit, with `...` elisions only.
- `write()` gets `path.join(__dirname, '<stem>.pptx')`, not a bare file
  name: a relative name resolves against the shell's working directory, and
  a run started from the repository would write the deck into it.

Run `cd <out> && node build.js`; it writes `<out>/<stem>.pptx` and prints
every warning.

## Notes

Every slide gets `notes({ min, say, ask, table, open })`. The build warns
on a slide whose notes lack `min` or `say`.

- `min`: the minutes the slide takes. deckkit sums them into the agenda and
  checks the total against `plan.md`'s length, so the agenda cannot drift
  from the slides.
- `say`: what the speaker says, in full sentences. The slide carries one
  point in as few words as it can; `say` carries the explanation, and is
  what someone presenting a deck they did not write reads first.
- `ask`: questions to put to the audience, where the slide has one worth
  asking.
- `table`: rows a diagram replaced on the slide (`teaching.md`, R3). The
  reference survives for the reader without competing with the diagram.
- `open`: claims the slide depends on that nothing has verified
  (`teaching.md`, R9), and every hand-derived step-through number, marked
  `hand-derived`. A replayed number instead names its `demo/` output file in
  `say`.

## Diagrams

Diagrams are drawn with deckkit's native shapes, never images or Mermaid. A
native shape stays editable when the owner's feedback lands in Phase 6, and
its labels are text the fact-check reviewer can extract and compare with
the code; an image is neither.

Pick the helper by the structure the outline's `learns` describes:

- components handing data to each other: `box()` and `arrow()`;
- work happening over time in parallel, or waiting on each other:
  `timeline()`, one lane per actor;
- a request and its replies between actors, in order: `sequence()`;
- a step-through of the hardest concept: one slide per state, the same
  boxes in the same places, so only what changed moves;
- genuinely tabular lookup content: `table()`, the last choice
  (`teaching.md`, R3).

## Fonts

The body and code fonts default to Microsoft YaHei and Consolas, and
`deck({ fonts: { body, code } })` overrides them from `plan.md`. YaHei
covers CJK and Latin in one face, so a mixed-language slide does not fall
back mid-line; Consolas is monospaced, so a code excerpt's columns line up
as they do in the editor.

deckkit's size estimates use per-character widths, not the font's metrics,
so a different font can fit where the estimate says it will not, or the
reverse. The rendered images in Phase 5 settle it.

## Warnings and their thresholds

Fix every warning by changing the content: shorten a title, cut an excerpt,
split a slide. `noFitCheck` silences one element, and is for an element
whose estimate is wrong, not one that is too full. List every use: the
visual reviewer checks each one in the render (`verification.md`).

These are the `LIMITS` in `deckkit.js`, each with its value and why it is
that value:

| Limit | Value | Reason |
|---|---|---|
| `titleMaxLines` | 1 | A title that wraps runs into the content below it, and a title that needs two lines usually names two points (`teaching.md`, R8). |
| `fitFloor` | 12 | Auto-fit shrinks text no further: below 12 pt a slide is hard to read on a shared screen, and text that does not fit at 12 pt is more than one slide holds. |
| `codeMinSize` | 11 | Code is never wrapped, because a wrapped line no longer matches the file the audience will open, so a long excerpt is shrunk instead; below 11 pt it cannot be read while the speaker talks over it. |
| `planTolerance` | 0.1 | Per-slide minutes are estimates and drift a little; a total off the plan by more than a tenth means the talk overruns its slot or is missing slides, and the outline needs revisiting. |
| `latinEm` | 0.55 | The estimated width of a non-CJK character. Most proportional Latin text averages narrower, so the estimate errs towards a warning rather than a missed overflow. |
| `wideEm` | 1.0 | CJK and full-width characters are drawn on a square em, one character per em. |
| `lineSpacing` | 1.2 | A line takes about 1.2 times its font size at single spacing. |

The build also warns when the notes lack `min` or `say` (above), and when
the total minutes are off the plan by more than `planTolerance`.

A warning that the content cannot be changed to fix is a decision the
outline got wrong: go back to `outline.md`, change the line, and have the
owner confirm the change before rebuilding.
