---
name: tutorial-deck
description: Turn a repository and a topic into a verified PPTX tutorial for developers who will read and change that code, with every claim cited to a pinned commit, derived, or omitted. User-invoked: type /tutorial-deck.
disable-model-invocation: true
---

# Tutorial Deck

Turn a repository and a topic into a slide deck that teaches developers new
to the topic's theory enough to read and modify the code. Every claim on a
slide is cited to the pinned commit, derived from something cited, taken
from an approved replay's output, or omitted. Six phases build the deck in
order; read each phase's own doc only when that phase is reached.

## Input

`/tutorial-deck <repo> <topic>`. `<repo>` is a directory; `<topic>` names
one mechanism, subsystem or behaviour of that code, in words: "request
scheduling", "the KV cache eviction". With either missing, ask for it; a
deck about a whole repository has no main line to follow.

## Resolve the skill directory

Resolve `${CLAUDE_PLUGIN_ROOT}/skills/tutorial-deck` first; if that path does
not exist, fall back to the directory this `SKILL.md` was read from. Bind
whichever resolves as `<skill-dir>` for the rest of this document and every
phase doc it points to.

Every command goes through the project's own command wrapper when it has
one, never a bare host binary. If the wrapper cannot reach `<skill-dir>` (a
container mount boundary), copy `<skill-dir>/deckkit.js` into the output
directory and have `build.js` require the copy: it is the only file from
the skill directory that a command loads.

## Output directory and the read-only rule

The interview's first question fixes the output directory, `<stem>_deck/` by
default (`<skill-dir>/interviewing.md`). An existing directory at that path
stops the run with a question; this skill never writes into a directory it
did not create. Everything the run produces lands there:

- `survey.md`, `plan.md`, `outline.md` -- the record of what was found and
  what was decided, in the order it was decided.
- `build.js` and its `node_modules/` -- the deck's source and its pinned
  `pptxgenjs`.
- `demo/` -- the approved replay script and its captured output.
- `<stem>.pptx`, `<stem>.pdf`, `render/` -- the deck, its LibreOffice
  render, the page images and the extracted `render/text.md`.
- `reviews/` -- every review round's findings and dispositions.

**The repository is read-only for the whole run.** Nothing is written,
formatted, installed or cached outside the output directory, and the
replay suppresses its language's cache writes into the repository
(`<skill-dir>/../implementation-study/experiments.md`). Until the first
question is answered there is no place to write, so Phase 1 holds
`survey.md` as a draft.

Commands run from two places. `git`, `gh` and the replay run against the
repository, from its root, through its wrapper, and read only. `npm`,
`node`, `soffice` and `pdftoppm` run with the output directory as their
working directory (`cd <out> && node build.js`), so a relative path in any
of them cannot land in the repository.

## Pipeline

Read each phase's doc when that phase is reached, not before.

1. **Survey** -- read `<skill-dir>/surveying.md`. Pins the commit, reads
   the code, design docs and issues for the topic only, and drafts
   `survey.md`: concepts, mechanisms, design decisions with their rejected
   alternatives, real incidents, and runnable cores.
2. **Interview** -- read `<skill-dir>/interviewing.md`. Fixes the output
   directory first, then settles one decision per question, each with a
   recommended answer grounded in `survey.md`. Ends in `plan.md`, which the
   owner confirms.
3. **Outline** -- read `<skill-dir>/outlining.md` and
   `<skill-dir>/teaching.md`. Writes `outline.md`, one line per slide,
   self-checks it against the hard rules, and runs the approved replay for
   the hardest concept under
   `<skill-dir>/../implementation-study/experiments.md`, which ships in the
   same bundle. The owner confirms the outline.
4. **Build** -- read `<skill-dir>/building.md`. Installs the pinned
   `pptxgenjs`, writes `build.js` on `<skill-dir>/deckkit.js`, and fixes
   every build warning before anything is rendered.
5. **Verify** -- read `<skill-dir>/verification.md`. Renders the deck, then
   dispatches three independent reviewers -- fact-check, visual, narrative
   -- spot-checks each finding's basis, fixes, and repeats on the changed
   slides until a round has no definite finding or three rounds have run.
6. **Revise** -- read `<skill-dir>/revision.md`, only when the owner sends
   feedback on the verified deck. Proposes changes, edits only what the
   owner confirms, and re-verifies the changed slides.

## Degradation

Every row is said in the final report; none is worked around silently. The
phase doc named in each row owns the detail.

| Situation | Response |
| --- | --- |
| no Node or npm, or the `pptxgenjs` install fails | Stop (`building.md`). There is no fallback renderer: a deck built any other way has none of the build-time checks. |
| no LibreOffice or no poppler | Build and fix the warnings, extract `render/text.md`, run the fact-check and narrative reviews on it; skip the visual review and say so (`verification.md`). |
| uncommitted changes in the topic's files | Stop and ask whether to commit, stash, or study the committed version (`surveying.md`). |
| the repository is not a git repository | Pin the absolute path and the date; report that the citations have no version baseline (`surveying.md`). |
| issues and pull requests unreachable | Say so in `survey.md` and leave its incidents empty rather than inventing typical ones (`surveying.md`). |
| no runnable core, or the replay not approved | Hand-derive the step-through, mark each such number in the slide notes, and list those slides (`outlining.md`). |
| a declared font missing on the render machine | Render anyway; tell the visual reviewer and the report that the images show a substitute (`verification.md`). |
| no subagents | Run the three reviews in sequence, each against its own brief only, and report them as not independent (`verification.md`). |
| the output directory already exists | Stop and ask for another path (`interviewing.md`). |

## Requirements

Node and npm, with network access to install the pinned `pptxgenjs` into
each deck's directory; LibreOffice (`soffice` or `libreoffice`) and poppler
(`pdftoppm`) for the render; `fc-list` to check the declared fonts; `git`
for the pin, and `gh` or the host's equivalent to read issues. The replay
needs whatever the project's own wrapper needs to run its code.

## Final report

Report the deck's path and the pin, then everything the phases said must
reach the report: each degradation row that applied, the slides carrying
hand-derived numbers, every `noFitCheck` use, that the images are
LibreOffice's render and not PowerPoint's, and every review finding still
open, with its slide and why.

## Why this pipeline and not something simpler

A deck written straight from reading the code reads well to its author and
fails its audience, and every phase exists to catch one way it fails.

- **The interview comes before the outline** because the decisions that
  shape a tutorial -- what the audience already knows, what the main line
  follows, which concept is hardest -- are the owner's, and each one changes
  every slide after it. Settled one at a time with a grounded
  recommendation, they cost a sentence each; discovered in a finished deck,
  they cost a rebuild.
- **The outline comes before the build** because a deck's structural faults
  -- a mechanism with no failure before it, a throughline named after its
  first instance, a slide with two points -- are obvious in a list of
  one-line slides and invisible in finished ones.
- **The deck is built in code on `deckkit.js`, with native shapes**, because
  a program can warn about what it can measure (a title that wraps, code too
  small to read, minutes off the plan) before anyone looks, and a native
  shape stays editable for Phase 6 and is text the fact-checker can extract.
  An image or a Mermaid render is neither.
- **Three reviewers, none given the author's reasoning**, because the
  author reads the deck with the code and the outline in mind and fills
  every gap without noticing it. Fact, layout and narrative are different
  failure classes that one reader blends together, and a reviewer handed
  the reasoning checks the reasoning and agrees with it.
- **The author spot-checks every finding before fixing it**, because
  reviewers are independent and can be wrong, and a fix on a wrong basis
  puts an error into a deck that was right.
- **The stop rule is three rounds**, because findings that keep coming after
  three rounds point at the outline, not at slides, and more slide fixes do
  not converge.
