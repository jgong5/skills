---
name: implementation-study
description: Turn one algorithm implementation into a verified PDF study with every substantive claim cited, derived, or measured. User-invoked: type /implementation-study.
disable-model-invocation: true
---

# Implementation Study

Turn one algorithm implementation into a study document and a verified PDF:
every claim in the output is cited to a specific line in the code under
study, derived by reasoning from something already cited, measured by an
approved experiment, or omitted. Five phases build that document in order;
read each phase's own doc only when that phase is reached.

## Input

Accept exactly one of two forms: `path/to/file:symbol` or `path/to/file`.
Anything else -- a bare symbol name with no path, a directory, a
natural-language description like "the queue implementation" -- is not a
resolved entry point. If the input resolves to more than one file or symbol,
stop and ask which one is meant; do not guess on the user's behalf. `<stem>`
is the symbol name when one is given, otherwise the file's stem (`bfs.py` ->
`bfs`); every output path this skill produces is built from `<stem>`.

Reject code that is generated, vendored, or minified -- paths under
`vendor/`, `third_party/`, `node_modules/`, `*.min.*`, or a file carrying a
"generated" / "do not edit" header. Stop instead of studying it: nobody
wrote the design decisions this pipeline exists to recover.

## Resolve the skill directory

Resolve `${CLAUDE_PLUGIN_ROOT}/skills/implementation-study` first; if that
path does not exist, fall back to the directory this `SKILL.md` was read
from. Bind whichever resolves as `<skill-dir>` for the rest of this document
and every phase doc it points to. If the project's command wrapper cannot
reach `<skill-dir>` (a container mount boundary, a sandboxed build), do not
fall back to running a bare host interpreter -- copy only the one helper
script the current step actually invokes into the output directory and run
it from there, through the wrapper, so every execution still goes through
the project's own toolchain.

## Resolve output paths

Starting at the entry-point file, walk upward to the nearest ancestor
directory containing `docs/`; use that `docs/` as the output directory. If
no ancestor has one, use the entry-point file's own directory instead.
Every study produces exactly five output forms there, all named from
`<stem>`:

- `<stem>_study.md` -- the study document.
- `<stem>_study.notes.md` -- the comprehension ledger.
- `<stem>_study_experiments/` -- approved experiment scripts, captured
  output, and `ENV.md` files.
- `<stem>_study.integrity.json` -- the non-git snapshot baseline (only when
  the repository under study is not a git work tree).
- `<stem>_study.pdf` -- the rendered, verified deliverable.

Resolve every one of these paths before any phase does any work, and check
that none of them already exists. This skill creates files; it never
overwrites one. An existing file at one of these names means either a prior
run to resume or review, or a name collision with something unrelated --
either way, stop and say so rather than silently clobbering evidence the
skill did not produce. State plainly, before Phase 1 begins, that these five
paths are new and that everything this run produces is confined there.

## Safety invariant

The repository under study is read-only for the life of this skill: it
modifies or deletes nothing outside the output directory just resolved.
Phase 1 establishes the mechanism that makes this checkable rather than
assumed -- a clean `git status` baseline for a git work tree, or a
`check_evidence.py snapshot` baseline otherwise -- and Phase 5's evidence
pass proves, mechanically, that the repository came out exactly as it went
in. Every phase that touches the filesystem writes only inside the five
paths above (experiment artifacts go under `<stem>_study_experiments/`); a
phase that finds itself wanting to edit, format, or "just quickly fix"
something in the repository under study has left the scope of this skill.

## Pipeline

Read each phase's doc only when that phase is actually reached -- not
before, and not all five up front. A phase that has not started yet does
not need its rules loaded, and loading them early is how a later phase's
vocabulary leaks backward into an earlier one's ledger.

1. **Analyze** -- read `<skill-dir>/analysis.md`. Resolves the boundary, the
   contract, the caller map, and opens the comprehension ledger; establishes
   the integrity baseline.
2. **Investigate** -- read `<skill-dir>/investigation.md`. Turns the ledger
   into a decision inventory: the implementation choices, their
   alternatives, and the trade-off between them. Read
   `<skill-dir>/experiments.md` only when a trade-off is genuinely unclear
   without running code -- derivation from what Phase 1 already established
   settles most of them without it.
3. **Write** -- read `<skill-dir>/writing.md`. Turns the ledger and the
   decision inventory into `<stem>_study.md`: the fixed spine, the derived
   middle, decision blocks, and back matter. Discovers nothing new; a
   sentence that needs evidence Phase 1 or Phase 2 did not produce is a sign
   to go back, not to write around it.
4. **Render** -- read `<skill-dir>/rendering.md`. Turns `<stem>_study.md`
   into `<stem>_study.pdf`; it invokes `<skill-dir>/make_pdf.py` and
   `<skill-dir>/tutorial.css`, and classifies any overlong code line before
   touching either.
5. **Verify** -- read `<skill-dir>/verification.md`. The gate: it invokes
   `<skill-dir>/check_pdf.py` and `<skill-dir>/check_evidence.py`, plus a
   manual read-through, and routes every finding back to Phase 1, Phase 2,
   Phase 3, or `tutorial.css` -- never fixed at the pass that happened to
   catch it.

## Degradation

Every row below is a stop-and-say-so, not a silent workaround. Guessing
past one of these produces a study that reads as confident and is not.

| Situation | Response |
| --- | --- |
| entry point ambiguous: resolves to more than one file or symbol | Stop and ask the user which one is meant; do not pick for them. |
| no callers found anywhere in the repository | State plainly, in Phase 3's "Where it sits" section, that there are no callers, rather than omitting the section. |
| no canonical form to depart from (the implementation is bespoke) | State plainly, in Phase 3, that no canonical form exists, and describe the design as a whole instead of a delta from a standard one. |
| no tests exist for the entry point | Derive the contract only from the signature, docstring, and in-repo callers Phase 1 can actually read -- do not invent behavior the code does not demonstrate. |
| the repository under study is not a git repository | Run `check_evidence.py snapshot` in Phase 1 instead of a clean `git status`, and pass `--snapshot` to `check_evidence.py verify` in Phase 5. |
| experiments declined by the user, in full or in part | Record the decline in the experiment's `PLAN.md` and in the ledger, then derive an answer from what is already known or omit the claim. |
| the code under study is generated, vendored, or minified | Stop before Phase 1 starts; a study of code nobody hand-wrote has no design decisions to recover. |
| an honest trace would make the boundary too large to read closely | Declare a narrower boundary, and preserve every excluded component for the Boundary note, so a reader can tell what was deliberately excluded from what was simply missed. |
| Chrome/Chromium is missing at Render preflight | Stop and point the user at the project's Chrome-install help (e.g. `gpu_docker/install-chrome.sh`) by name; do not install a substitute browser. |
| `pandoc` is missing at Render preflight | Stop and report the gap; a missing `pandoc` is an environment problem, not a document problem, and downgrading the render to work around it is not an option. |

## Requirements

Python 3, `pandoc`, a Chrome-family binary (Chrome or Chromium), the
`websockets` Python package, and `poppler-utils` (`pdftotext`, `pdffonts`,
`pdfinfo`, `pdftoppm` -- everything `check_pdf.py` and the Phase 5
sample-page rasterization step call by name). Every project command this
skill runs -- `make_pdf.py`, `check_pdf.py`, `check_evidence.py`, and any
approved experiment script -- goes through the project's own command
wrapper, never a bare host interpreter; see `<skill-dir>/experiments.md`
for why that matters most for code borrowed from the repository under
study.

## Final checklist

Do not report the study finished until every line below is true:

- The study boundary is disclosed, with every excluded component named in
  the Boundary note.
- The fixed spine's five sections open `<stem>_study.md`, in order, each
  present -- even where a section is one honest sentence.
- Every substantive claim carries at least one ledger ID, checked by a full
  read-through, not only by `check_evidence.py`'s mechanical pass.
- Every decision block has all three literal parts -- `**Decision.**`,
  `**Alternatives.**`, `**Why this one.**` -- at column zero, in order.
- Every Improvements entry is falsifiable: a reader could go check the
  stated condition and find it false.
- Every experiment has a recorded approval or decline in its `PLAN.md`, and
  every approved experiment has its script, captured `.out`, and `ENV.md`
  in `<stem>_study_experiments/`.
- `check_pdf.py` exits clean.
- `check_evidence.py verify` exits clean.
- Every page `check_pdf.py`'s sample-page table names has actually been
  rasterized and looked at.
- No file that existed before this run started has been changed or
  deleted.
