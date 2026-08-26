---
name: architecture-study
description: Review a working software system's architecture and turn the review into a diagram-first verified PDF -- paradigms, contracts, the traced execution loop, trade-offs, blocking mechanisms, and alternative designs, with every claim witnessed in the code. User-invoked: type /architecture-study.
disable-model-invocation: true
---

# Architecture Study

Read a system that already exists and produce two things: a study document
and a verified PDF, laid out as seven fixed sections that answer the same
seven questions every time. The report is a whiteboard session held with a
peer, not a tutorial and not a code review -- it explains the design the code
actually has, why that design emerges from the constraints it faces, what it
costs, and where it will break first.

Six phases build the report in order; read each phase's own doc only when that
phase is reached.

## Input

Accept a directory: the system or subsystem to study. With no argument, the
current working directory is the system. A single file is not an architecture
-- if the input names one, ask whether the surrounding package is meant, or
send the user to `/implementation-study`, which studies one algorithm in one
file.

`<stem>` is the directory's name (`serving/engine` -> `engine`); every output
path is built from it. When the directory holds several systems that share
nothing but a parent -- unrelated packages in a monorepo -- stop and ask which
one is meant rather than reviewing an accident of the filesystem.

Reject code that is generated, vendored, or minified: paths under `vendor/`,
`third_party/`, `node_modules/`, `*.min.*`, or a tree whose files carry a
"generated" / "do not edit" header. There are no design decisions to recover
from a tree nobody designed.

The user may name the report's reader when invoking. Absent that, the reader
is the one the altitude rule below describes.

## Resolve the skill directory

Resolve `${CLAUDE_PLUGIN_ROOT}/skills/architecture-study` first; if that path
does not exist, fall back to the directory this `SKILL.md` was read from. Bind
whichever resolves as `<skill-dir>` for the rest of this document and every
phase doc it points to. If the project's command wrapper cannot reach
`<skill-dir>` (a container mount boundary, a sandboxed build), do not fall
back to a bare host interpreter -- copy only the one helper script the current
step invokes into the output directory and run it from there, through the
wrapper, so every execution still goes through the project's own toolchain.

## Resolve output paths

The repository boundary governs this section: the repository root is the same
boundary `check_evidence.py` takes as `--repo-root`, and nothing below ever
proposes an output location outside it. Starting at the studied directory,
walk upward to the nearest ancestor containing `docs/`, but never past the
repository root -- an ancestor `docs/` outside the repository is not a
candidate however close it sits. When such a `docs/` exists inside the
repository, it is the output directory.

If none exists, the studied directory itself is the only remaining candidate,
and never adopted silently: name it to the user and get explicit approval
before Phase 1 does any work. The repository root itself is never valid --
`check_evidence.py` rejects it, because an output directory equal to the root
would make every path in the repository count as "inside the output
directory" and the Phase 6 no-modification check would pass no matter what
changed. When the studied directory is the repository root and no `docs/`
exists, stop and ask the user to name an output subdirectory; do not create or
guess one.

Every study produces exactly four output forms there, all named from `<stem>`:

- `<stem>_architecture.md` -- the study document.
- `<stem>_architecture.notes.md` -- the evidence ledger and the four
  inventories that feed it.
- `<stem>_architecture.integrity.json` -- the non-git snapshot baseline (only
  when the system under study is not in a git work tree).
- `<stem>_architecture.pdf` -- the rendered, verified deliverable.

Resolve all four before any phase does work, and check that none exists. This
skill creates files; it never overwrites one. An existing file at one of these
names means either a prior run to resume or a collision with something
unrelated -- either way, stop and say so. State plainly, before Phase 1
begins, that these paths are new and that everything this run produces is
confined there.

## Safety invariant

The system under study is read-only for the life of this skill: nothing
outside the output directory is modified or deleted. Phase 1 establishes the
mechanism that makes this checkable rather than assumed -- a clean `git
status` baseline in a work tree, or a `check_evidence.py snapshot` baseline
otherwise -- and Phase 6 checks it mechanically. Know what that covers: in a
work tree it is exactly what `git status` reports, which excludes paths
`.gitignore` matches. Run nothing that writes: this skill reads code, and a
phase that finds itself wanting to run the test suite, start the service, or
"just quickly fix" a lint error has left its scope.

## Altitude

The report holds one altitude, and every phase is calibrated to it. The reader
has a decade in AI infrastructure, workload optimisation, and low-level
performance work. They know what a thread pool, a futex, a page fault, a
protocol buffer, and a memory arena are; they do not need them introduced.
What they want is the mechanism one level below the abstraction they can
already see: not that the scheduler is asynchronous but which task holds which
lock across which await; not that the compiler has passes but what
intermediate representation each pass mutates and who owns the memory.

Holding altitude cuts both ways. Explaining a language feature is below it.
Restating a design as an adjective -- "clean separation of concerns", "loosely
coupled", "well abstracted" -- is above it, because a reader cannot check an
adjective. Every judgement lands on something a peer could go and disagree
with: a named type crossing a named boundary, a call that blocks, a field two
components both write.

Write in the register of a whiteboard session between peers: think out loud,
draw first and narrate second, name what you are unsure of instead of
smoothing it over, and address the reader as an equal who will push back.

## The witness rule

Every paradigm, contract, constraint, and coupling the report names carries a
**witness**: the code structure that instantiates it, cited to `path:line` in
the ledger. A pattern is not witnessed by its name appearing in a class name,
a docstring, or a directory called `pipeline/` -- it is witnessed by the
structure that makes the pattern true whether or not anyone wrote the word
down: the dispatch table, the queue handoff, the shared mutable store, the
visitor over a node type.

The rule bites hardest on constraints. "Python holds a Global Interpreter
Lock" and "model calls are latency-bound" are facts about the world, not
findings about this system, and they will write themselves into any report
that does not stop them. A constraint reaches section 5 only when the ledger
names the call site that blocks, the object that grows without a bound, the
lock held across the await, or the queue with no backpressure. A mechanism
with no witness is a question for section 7, not a finding for section 5.

## Pipeline

Read each phase's doc only when that phase is actually reached -- not before,
and not all six up front. A phase that has not started does not need its rules
loaded, and loading them early is how a later phase's vocabulary leaks
backward into an earlier phase's inventory.

1. **Survey** -- read `<skill-dir>/survey.md`. Establishes the integrity
   baseline, declares the boundary, and builds the component inventory and the
   contract inventory. Read `<skill-dir>/paradigms.md` when naming the
   paradigm a component's structure witnesses.
2. **Trace** -- read `<skill-dir>/tracing.md`. Follows one concrete execution
   from entry to exit through the components Phase 1 read, recording state
   mutations, ownership transfers, allocations, and every point where it
   blocks. Produces the step trace and the constraint inventory.
3. **Weigh** -- read `<skill-dir>/weighing.md`. Turns the three inventories
   into a decision inventory: the structural choices, their realistic
   alternatives, the deciding constraint, and the alternative paradigms that
   would win under different constraints.
4. **Write** -- read `<skill-dir>/writing.md` and `<skill-dir>/diagrams.md`.
   Turns the four inventories into `<stem>_architecture.md`: the seven-section
   spine, the four required figures, decision blocks, footnoted
   abbreviations, and the guided-exploration close. As its final action, runs
   `check_evidence.py materialize-ledger` to project the notes ledger into a
   terminal Evidence ledger and cross-link every mark to its definition and
   back. Discovers nothing new; a sentence or an edge that needs evidence the
   earlier phases did not produce is a sign to go back.
5. **Render** -- read `<skill-dir>/rendering.md`. Turns the markdown into
   `<stem>_architecture.pdf` through `<skill-dir>/make_pdf.py` and
   `<skill-dir>/tutorial.css`, classifying any overlong code line first.
6. **Verify** -- read `<skill-dir>/verification.md`. The gate: it invokes
   `<skill-dir>/check_pdf.py` and `<skill-dir>/check_evidence.py`, plus a
   manual read-through, and routes every finding back to the phase that caused
   it -- never to the pass that caught it.

## Degradation

Every row is a stop-and-say-so, not a silent workaround. Guessing past one
produces a report that reads as confident and is not.

| Situation | Response |
| --- | --- |
| the input is one file, not a system | Ask whether the surrounding package is meant, or point the user at `/implementation-study`. |
| the directory holds several unrelated systems | Stop and ask which one; do not review a filesystem accident. |
| the system is too large to read closely | Declare a narrower boundary and name every excluded component in the `**Boundary.**` block, so a reader can tell what was deliberately left out from what was simply missed. |
| a component is named but never opened | It is outside the boundary. Describe what crosses its edge and say plainly that its internals were not read; do not describe them. |
| the code exhibits no recognizable paradigm | Say so plainly and describe the structure the code actually has. A named pattern asserted without a witness is worse than no name at all. |
| there is no single core execution loop | Trace the path the callers exercise most, name which one it is, and say plainly how the others differ. |
| a structural choice has no realistic alternative | Write it as ordinary prose, not a decision block. A block manufactured to fill section 4 teaches nothing. |
| a suspected bottleneck has no witness | It becomes a section 7 question, not a section 5 finding. |
| the system under study is not in a git work tree | Run `check_evidence.py snapshot` in Phase 1 and pass `--snapshot` to `verify` in Phase 6. |
| the code under study is generated, vendored, or minified | Stop before Phase 1 starts. |
| the studied directory is the repository root and no `docs/` exists | Stop and ask the user to name an output subdirectory inside the repository. |
| Chrome/Chromium is missing at Render preflight | Stop and point the user at the project's Chrome-install help (e.g. `gpu_docker/install-chrome.sh`) by name; do not install a substitute browser. |
| `pandoc` is missing at Render preflight | Stop and report the gap. A missing `pandoc` is an environment problem, not a document problem. |
| a `poppler-utils` tool (`pdftotext`, `pdffonts`, `pdfinfo`, `pdftoppm`) is missing at Verify preflight | Stop and name the missing tool and the package that provides it; do not skip the pass or report it clean without running it. |

## Requirements

Python 3, `pandoc`, a Chrome-family binary (Chrome or Chromium), the
`websockets` Python package, and `poppler-utils` (`pdftotext`, `pdffonts`,
`pdfinfo`, `pdftoppm` -- everything `check_pdf.py` and the Phase 6 sample-page
rasterization call by name). Every command this skill runs goes through the
project's own command wrapper, never a bare host interpreter.

## Final checklist

Do not report the study finished until every line below is true:

- The `**Boundary.**` block names what was read and every component that was
  deliberately excluded.
- The seven spine sections are present, titled verbatim, in order, each
  answered -- even where the honest answer is one sentence.
- Every paradigm, contract, constraint, and coupling the report names has a
  witness in the ledger; nothing in section 5 rests on a fact about the
  language or the hardware alone.
- The `system-decomposition`, `contract-map`, `execution-lifecycle`, and
  `tradeoff-landscape` inline SVG figures are present; each has accessible
  metadata, a numbered caption, an adjacent cited interpretation, and only
  relationships an inventory established.
- Every decision block has all three literal parts -- `**Decision.**`,
  `**Alternatives.**`, `**Why this one.**` -- at column zero, in order.
- Every abbreviation is spelled out and footnoted at its first use in prose,
  and spelled out exactly once.
- Section 7 closes on two to four questions, each aimed at a boundary the
  report could not settle.
- Every substantive claim carries at least one ledger ID, checked by a full
  read-through and not only by `check_evidence.py`'s mechanical pass.
- `check_pdf.py` exits clean.
- `check_evidence.py verify` exits clean.
- Every page `check_pdf.py`'s sample-page table names has been rasterized and
  looked at.
- No file that existed before this run started has been changed or deleted.
