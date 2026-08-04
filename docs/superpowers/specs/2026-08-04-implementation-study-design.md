# implementation-study -- design

Date: 2026-08-04

## Summary

A new skill, `implementation-study`, that turns one algorithm implementation
in source code into a verified PDF study document. The document explains what
the implementation does, the context it lives in, why each non-obvious choice
was made rather than a named alternative, and how it could be improved. Every
asserted claim is cited to a real file and line, derived from cited claims
with the reasoning shown, or measured by a recorded experiment -- never
guessed. Claims that cannot be grounded any of those three ways are omitted.

The skill is a sibling of the existing `asm-tutorial`, with its own copy of the
render and verify machinery. It ships in its own marketplace bundle and is
user-invoked only.

## Motivation and scope

`asm-tutorial` already produces a verified PDF walkthrough, but only for AMD
CDNA assembly listings. Its render/verify scripts (`make_pdf.py`,
`check_pdf.py`, `tutorial.css`) are already language-agnostic -- they know
markdown and PDFs, nothing about GPUs. Only `annotate_asm.py` and
`cdna-facts.md` are domain-specific.

`implementation-study` generalizes the *document* to any algorithm
implementation in any language, and extends it in two directions the sibling
does not cover:

- **Comparative rationale.** Why this way and not that way -- named
  alternatives with grounded trade-offs.
- **Improvement analysis.** Where the implementation could be better, stated
  falsifiably.

It also gains a capability the sibling does not have: it may create and run
experiments -- probes, tests, benchmarks -- to ground claims that reading
alone cannot settle, subject to a user approval gate and a hard rule that the
repository under study is never modified.

### Out of scope

- Language-specific static analysis (no tree-sitter, no ctags, no parsers).
  Code reading is Claude's job, which is what makes the skill
  language-agnostic by construction.
- Automated git archaeology tooling. `git log -L` and `git blame` are
  prescribed as manual techniques in the methodology, but no script wraps
  them: they are slow on large repos and useless on shallow clones.
- Subsuming or modifying `asm-tutorial`. It stays as it is.

## Decisions taken during design

| Question | Decision |
| --- | --- |
| Relationship to `asm-tutorial` | Sibling; fork the machinery, as `asm-tutorial` itself forked it from `pr-review-dossier` |
| Input | An entry point (function, class, or file); the skill traces outward to a declared boundary |
| Audience | Competent engineer, new to this algorithm |
| Evidence rule | Cite, derive, or omit. Derivation counts when the reasoning is spelled out |
| Placement of rationale | Decision blocks inline; improvements collected in a final chapter |
| Tooling | Fork the three scripts, add one evidence checker; no code parsers |
| Invocation | User-invoked only (`disable-model-invocation: true`) |
| Execution | May create and run experiments in scratch; repo under study stays intact |
| Experiments | Require an approved plan before anything runs |
| Pipeline | Five phases, with Investigate separate from Analyze |
| Name | `implementation-study` |

Rejected alternatives and why:

- **Extracting a shared renderer** instead of forking would remove ~450 lines
  of duplication but couples two bundles and breaks the flat-skill-directory
  convention the repo relies on. Skills ship as self-contained directories with
  no shared-library mechanism.
- **Folding Investigate into Analyze** (a four-phase pipeline mirroring
  `asm-tutorial`) makes Analyze a grab bag and leaves the counterfactual
  discipline -- the part most likely to go wrong -- without a home.
- **A standalone Experiment phase** between Analyze and Write runs before the
  questions exist. Experiments are raised by the alternatives work, so they
  belong inside Investigate as a technique.
- **Graded evidence with `(inferred)` markers**, as `asm-tutorial` uses for
  missing-source cases, was rejected in favor of strict omission. A confident
  wrong explanation does the most damage in exactly the sections this document
  exists for.

## The document

### Fixed spine

Every study opens with these, in this order:

1. **What it computes.** The contract: inputs, outputs, preconditions,
   postconditions, failure behavior. Cited to signature, docstring, and tests.
2. **Where it sits.** Real call sites found in the repo, the path from the
   nearest public API, and what depends on it. Grounded in actual callers, not
   an assumption about intent.
3. **Background and the canonical algorithm.** Only the concepts load-bearing
   in this implementation -- not a survey of the field -- plus the textbook
   form of the algorithm (short pseudocode or statement, complexity, standard
   name) with citations to a paper or reference.
4. **How this implementation departs from the canonical form.** The deltas.
   Each delta is a decision that either resolves here or forward-references a
   decision block in the body.
5. **Data structures and invariants.** The state carried and what must remain
   true, derived from the code.

### Derived middle

Walk the implementation in its own structure -- setup, main loop, edge cases,
teardown, whatever it actually has -- not from a template. Favor explaining
representative code over every line, the same way `asm-tutorial`'s body does.

### Decision blocks

Inline, where the reader meets the code:

    **Decision.** <what the code does>
    **Alternatives.** <one to three realistic other choices>
    **Why this one.** <cited or derived trade-off>

A choice earns a block only if a competent engineer could plausibly have
written it the other way *and* the difference would matter. Without that bar,
`for i in range(n)` gets a block and the format becomes noise.

An alternative must be concrete enough to be checkable: "a hash map keyed on
the tile index", not "a better data structure". A trade-off with no
checkable content is an omission case, not a hedging case.

### Back matter

- **Improvements.** A separate chapter, not scattered inline, because critique
  is a different register from teaching and the reader should be able to take
  it or leave it. Each improvement states what would change and what would have
  to be true for it to be a win -- falsifiable, not asserted.
- **Boundary note.** What was treated as a black box, and why.
- **Sources.** External references cited in the body.

### Degradation of the spine

Omission over invention. If there is no canonical form because the algorithm
is bespoke, section 3 says so plainly and section 4 becomes "the design as a
whole" rather than a diff. A fabricated textbook version, invented so there is
something to compare against, is the specific failure this rule prevents.

## Pipeline

Five phases, each with one reference doc read on demand.

| Phase | Doc | Produces |
| --- | --- | --- |
| 1. Analyze | `analysis.md` | boundary resolved; comprehension ledger |
| 2. Investigate | `investigation.md`, plus `experiments.md` on demand | decision inventory; alternatives; derived or measured trade-offs; ledger extended |
| 3. Write | `writing.md` | `<stem>_study.md` |
| 4. Render | `rendering.md` | `<stem>_study.pdf` |
| 5. Verify | `verification.md` | pass, or a finding |

### Failure loop

- A render or layout finding goes back to Phase 3 (the markdown) or to
  `tutorial.css`, classified before re-rendering -- the same rule and the same
  reasoning as `asm-tutorial`'s Phase 4.
- A **citation** finding goes back to Phase 1 or 2 instead. The ledger is
  wrong; editing the prose to match a bad ledger launders the error rather
  than fixing it.

`verification.md` must state this split explicitly.

## Files on disk

### Skill directory (`skills/implementation-study/`)

    SKILL.md            spine: paths, phases, checklist, degradation, requirements
    analysis.md         Phase 1
    investigation.md    Phase 2
    experiments.md      Phase 2, read on demand
    writing.md          Phase 3
    rendering.md        Phase 4
    verification.md     Phase 5
    make_pdf.py         forked from asm-tutorial
    check_pdf.py        forked, plus the decision-block check
    tutorial.css        forked
    check_evidence.py   new

`tutorial.css` keeps its name rather than being renamed to match the skill.
`rendering.md`'s code-sizing arithmetic quotes the file by name, and keeping
the name makes a three-way diff against the other two forked copies trivial
when one of them gets a fix worth propagating.

There is no per-target facts file. `cdna-facts.md` exists in the sibling
because GPU constants vary by architecture; this skill has nothing analogous
to maintain.

### Entry point and stem

The skill takes one entry point in either form:

    path/to/file.py:symbol_name      a function or class within a file
    path/to/file.py                  the file, when it holds one algorithm

`<stem>` is the symbol name when one is given, otherwise the file stem. Two
studies of different functions in the same file therefore do not collide on
their output filenames.

### Output directory

The repository root -- the same boundary `check_evidence.py` takes as
`--repo-root` -- is the outer edge of the search below; nothing in this
section ever proposes a location outside it.

Starting at the entry point's file, walk upward looking for the nearest
ancestor directory containing a `docs/` subdirectory, but the walk stops at
the repository root: an ancestor `docs/` that lives outside the repository is
never a candidate, no matter how close it sits to the entry point, because
the repository boundary governs the search, not proximity. When such a
`docs/` exists inside the repository, use it.

Otherwise, fall back to the entry point's own directory -- but only when that
directory is strictly inside the repository root, and only with the user's
explicit approval, named and confirmed before any phase does work, because it
is a guess about where output belongs rather than a resolved convention like
an existing `docs/`. When the entry point's own directory *is* the repository
root and no ancestor `docs/` exists inside the repository, there is no valid
fallback at all: stop and ask the user to name an output subdirectory
strictly inside the repository, rather than creating `docs/` on their behalf
or guessing a name. `check_evidence.py` rejects an `--output-dir` equal to
`--repo-root` outright, so this is not merely a style preference: an output
directory at the repository root would make every path in the repository
count as "inside the output directory," and Phase 5's no-modification check
would report clean no matter what changed.

    <docs>/<stem>_study.md                    the study document
    <docs>/<stem>_study.notes.md              the ledger, kept as audit trail
    <docs>/<stem>_study_experiments/          scripts, captured output, PLAN.md, ENV.md
    <docs>/<stem>_study.integrity.json        non-git integrity snapshot, when needed
    <docs>/<stem>_study.pdf                   the render

**Repo integrity rule:** the skill creates only new files, all under that one
output directory, and modifies or deletes nothing that already existed.

## The evidence system

### Ledger format

Markdown, one claim per entry, regular enough to parse and writable by hand.
Lives at `<docs>/<stem>_study.notes.md`.

    - [C1] The accumulator is float32. cite: attention.py:112 `acc = zeros(..., dtype=float32)`
    - [C2] The reduction sums 4096 terms. derive: C1, attention.py:118 `for k in range(0, 4096, BLOCK)`
          -- trip count (4096/BLOCK) * BLOCK = 4096
    - [C3] float16 accumulation loses ~3 significant digits at this length.
          measure: flash_attention_fwd_study_experiments/acc_precision.py
          -> flash_attention_fwd_study_experiments/acc_precision.out

Grammar: `- [ID] <claim>. <class>: <source>`, continuation lines indented.

Path bases differ by class and `check_evidence.py` resolves them accordingly:
`cite:` paths are relative to the root of the repo under study, because they
point into that repo; `measure:` paths are relative to the output directory,
because they point at artifacts the skill itself produced. Every `measure:`
entry implicitly refers to the single `ENV.md` in its experiments directory,
so it is not repeated per entry.

Three classes:

- **`cite:`** -- external support. A `path:line` or `path:line-line`, a commit
  SHA, an issue URL, a paper, or a documentation URL. Every `path:line`
  citation carries a **verbatim anchor** in backticks: without one, line
  numbers rot silently as the repo moves on; with one, drift is detectable and
  often locatable.
- **`derive:`** -- reasoning from other ledger entries and citations, with the
  arithmetic or logic spelled out inline. A derivation that is asserted rather
  than shown is not a derivation.
- **`measure:`** -- an experiment result. Names the script, its captured
  output file, and the environment manifest.

There is deliberately no fourth class for inference. An inferred claim is
omitted.

### `check_evidence.py`

One gate for "did the evidence discipline hold". It verifies:

1. Every citation's file exists and the cited line exists.
2. Every citation's anchor still appears at that line. When the anchor is
   found elsewhere in the file, report "moved to line N" rather than a bare
   failure.
3. Every id referenced in a `derive:` entry resolves to a ledger entry, and
   the derivation graph is acyclic.
4. Every `measure:` entry names a script and an output file that exist under
   the experiments directory, and an `ENV.md` that exists.
5. Every `measure:` entry corresponds to an approved entry in `PLAN.md`. An
   unplanned measurement is a discipline failure the same way an unresolvable
   citation is.
6. Every citation appearing in the prose has a ledger entry. The reverse is
   not an error -- unused ledger entries are ordinary research residue.
7. The repo under study is unmodified (see below).

The script is named for evidence rather than citations because repo integrity
is part of the same question and does not deserve a separate script.

**Stated limitation.** This catches bad citations, not *missing* ones. No
regex distinguishes an uncited assertion from ordinary connective prose.
Detecting a claim that skipped the ledger stays a Phase 5 read-through job,
and `verification.md` must say so plainly rather than letting a green checker
imply more than it proved.

### Repo integrity check

- **Under git:** every line of `git status --porcelain` must be `??` and every
  path must be inside the output directory.
- **Without git:** Phase 1 writes a recursive path/size/mtime listing of the
  repo under study -- excluding the output directory, whose whole purpose is to
  grow -- plus content hashes of the files the study cites, since a same-size
  same-mtime edit would otherwise slip through. The snapshot lands in the
  output directory as `<stem>_study.integrity.json`, and Phase 5 diffs against
  it.

## Experiments

`experiments.md` is read from Phase 2 only when a claim cannot be derived.
Derivation is the default; each experiment is a small research project.

### Approval gate

Before running anything, Phase 2 writes
`<docs>/<stem>_study_experiments/PLAN.md`: one entry per proposed experiment,
stating the claim it would ground, what it would actually run, rough runtime,
and what it would consume or change (accelerator time, packages installed,
scratch venv). Then it stops and presents the plan.

Four responses are supported: approve all, approve a subset, revise what is
measured or how, or skip entirely.

- **Skipping never stalls the pipeline.** A declined experiment's claim falls
  back to derivation, or is omitted. The cite-or-derive-or-omit rule already
  covers it, so there is no state in which the document cannot be finished.
  This is what makes it safe to decline everything.
- **Declines are recorded, not silently dropped.** The plan entry keeps the
  decision and the ledger notes the resulting absence. "This trade-off is
  unquantified because the benchmark was declined" tells the reader more than
  the claim's mere non-appearance, and it makes a later run resumable: one
  declined experiment can be revisited without redoing Phase 2.
- **Approval is per-plan, not blanket.** An experiment discovered mid-Phase-2
  -- likely, since working the alternatives raises questions -- goes back
  through the gate as a plan amendment. Otherwise one "yes" becomes an
  unbounded license, which is what the gate exists to prevent.

### Rules that make a measurement citable

- **Everything lands in the experiments directory.** If an experiment needs a
  modified version of the algorithm -- comparing against an alternative usually
  does -- copy the file into that directory and edit the copy. Never an in-tree
  edit reverted afterward; "reverted afterward" is how repos get dirty.
- **Every experiment is a script that reproduces its own result**, with its
  output captured to a file beside it. The ledger's `measure:` entry names
  both. A one-liner run in a shell and remembered is not evidence.
- **One `ENV.md` per run** -- machine, OS, accelerator, runtime and library
  versions, the commit SHA of the repo under study, date, and any package
  installed for an experiment. A timing without it is not a fact about
  anything. Prefer a scratch venv under the experiments directory over
  installing into an environment the project owns.
- **Run through the project's own command wrapper**, never a bare interpreter.
  The other skills in this repo already follow this rule; it matters more here
  because experiments actually execute.
- **Benchmark discipline.** Verify both sides compute the same thing before
  timing them. Warm up, repeat, and report a spread with the repetition count
  -- never a bare single number. Bound the runtime and record the bound. If a
  like-for-like comparison cannot be arranged, drop the claim instead of
  qualifying it into uselessness.
- **A failed experiment is a result.** It gets recorded, and the claim gets
  dropped or reversed. Quietly rerunning until the expected answer appears is
  the one failure mode that would poison everything downstream.

The docs must be plain that experiments execute code from the repo under
study, and that the skill adds no sandbox beyond not writing to it.

## Verification

Phase 5 runs three passes:

1. **`check_pdf.py`** (forked) -- fonts embedded, no wrapped code lines,
   cross-references resolve, page count, sample-page table. Plus one new
   structural check: every decision block has all three parts. A block that
   lost its **Alternatives** line is the exact defect the format exists to
   prevent, and it is unambiguous to detect.
2. **`check_evidence.py`** -- the gates listed above.
3. **Read-through** of the sampled pages, carrying the one job no script has:
   spotting an assertion that quietly skipped the ledger.

Spine completeness is deliberately *not* checked mechanically. Sections 3 and
4 legitimately degrade, so a rigid heading check would fire on correct
documents and end up disabled.

## Degradation

| Missing or blocked | Behavior |
| --- | --- |
| entry point ambiguous | stop and ask; never guess which function was meant |
| no callers found in repo | section 2 says so -- library boundary or dead code, both worth knowing |
| no canonical form | section 3 says so; section 4 covers the design as a whole |
| no tests | contract from signature, docstring, and code; edge-case claims needing a test are omitted |
| not a git repo | integrity via path/size/mtime snapshot plus cited-file hashes |
| experiments declined | claims fall back to derivation or omission |
| generated, vendored, or minified code | stop -- this skill studies human-written implementations |
| boundary too large to trace honestly | declare a narrower boundary and say so in the boundary note, rather than a shallow pass over everything |
| Chrome | stop; point at the project's own Chrome-install script if it has one |
| pandoc | stop; it is expected to be present, so its absence means something else is wrong |

## Packaging

A third marketplace bundle in `.claude-plugin/marketplace.json`:

    {
      "name": "implementation-study",
      "source": "./",
      "version": "0.1.0",
      "description": "Turn one algorithm implementation into a verified PDF study: what it computes, how it is used, why each choice was made rather than the alternatives, and how it could be improved -- every claim cited, derived, or measured.",
      "category": "engineering",
      "keywords": ["algorithm", "documentation", "tutorial", "pdf", "code-explanation"],
      "skills": ["./skills/implementation-study"]
    }

Not folded into `amd-gpu` or `pr-review-kit`. Bundles are the installation
unit, and every installed skill's description costs context in every session.
For the same reason `asm-tutorial` is *not* also listed in this bundle, even
though the manifest-only bundling would allow a skill to appear in two.

`SKILL.md` frontmatter carries `disable-model-invocation: true`. A description
broad enough to cover "explain any algorithm implementation" would otherwise
fire on casual "explain this function" requests and start a multi-phase PDF
pipeline nobody asked for. `asm-tutorial` can auto-fire safely because ".s
listing for gfx942" is a narrow trigger; this one is not.

Before pushing the manifest change, from the repo root on the host:

    claude plugin validate .
    claude plugin details implementation-study

`validate` checks schema only and will accept a `skills` entry pointing at a
directory that does not exist; `details` is the only thing that catches that.

`README.md` goes from two bundles to three.

## Testing

`tests/implementation_study/`, mirroring `tests/asm_tutorial/`, with a
`conftest.py` that puts `skills/implementation-study/` on `sys.path`.

- **`test_check_evidence.py`** -- the bulk of the new surface: citation
  resolution, anchor drift detection and relocation reporting, derivation
  cycle detection, `PLAN.md` linkage, prose-citation coverage, and repo
  integrity both under git and without it.
- **`test_check_pdf.py`** -- forked, plus the decision-block well-formedness
  check.
- **`test_make_pdf.py`** -- forked. Needs pandoc and Chrome in the container.
- **`test_reference_docs.py`**, **`test_skill_md.py`** -- ASCII enforcement,
  every `<skill-dir>/...` reference resolves, and the invariant sentences
  pinned, per repo convention.

No `cdna-facts` analog.

Tests run inside the ROCm container per the repo's `CLAUDE.md`:

    cd /md1/users/jgong5/gpu_docker
    ./shell.sh python3 -m pytest /workspace/skills/tests -q

## Cross-file couplings to document

`asm-tutorial`'s `CLAUDE.md` notes call out couplings that break silently when
edited one-sidedly. This skill adds three of its own, and each needs a comment
at both ends:

- **`writing.md`'s decision-block format and `check_pdf.py`'s block regex.**
  The literal `**Decision.**` / `**Alternatives.**` / `**Why this one.**`
  markers are a machine-readable contract, not a style preference. Rewording a
  label in the prose doc silently disables the check.
- **`writing.md`'s ledger grammar and `check_evidence.py`'s parser.** The
  `- [ID] <claim>. <class>: <source>` line shape and the backticked anchor
  convention are the same kind of contract.
- **`writing.md`'s heading and cross-reference conventions and
  `check_pdf.py`'s `HEADING_RE` / `XREF_RE`.** Inherited from the fork; it
  holds here for the same reason.

## Conventions this design inherits

- Every tracked file is ASCII: `--` for dashes, straight quotes.
- Prose in the skill explains *why* a mechanism exists, not only what it does.
- The skill resolves its own directory at runtime
  (`${CLAUDE_PLUGIN_ROOT}/skills/implementation-study`, falling back to where
  the file was read from) and defers to the project's own command wrapper
  rather than a bare `python3`.
