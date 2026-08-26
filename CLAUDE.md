# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code **plugin marketplace**, not an application. The product is prose:
each skill is a `SKILL.md` (instructions Claude follows) plus companion
reference docs it reads on demand, plus a few Python scripts the skill shells
out to. Three bundles ship from one marketplace entry -- `pr-review-kit`
(`pr-explain`, `pr-review-draft`, `pr-review-dossier`), `amd-gpu`
(`asm-tutorial`, `kernel-perf`), and `code-study` (`implementation-study`,
`architecture-study`). `README.md` is the user-facing documentation for all
three; keep it in sync when a bundle's skills, requirements, or install story
change.

## Commands

Tests run **inside the ROCm container**, per `/md1/users/jgong5/CLAUDE.md` and
`gpu_docker/CLAUDE.md`. The host `python3` is 3.6 with no pytest; the
container's is 3.12. Host path `/md1/users/jgong5` is container path
`/workspace` -- edit on the host, run in the container.

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests -q            # whole suite
./shell.sh python3 -m pytest /workspace/skills/tests/asm_tutorial/test_check_pdf.py -v
./shell.sh python3 -m pytest /workspace/skills/tests -k wrapped_lines -v   # one test
```

Each suite's `conftest.py` puts its own skill directory on `sys.path`, so tests
import the scripts by bare module name (`import check_pdf`). There is no
package install step and no test runner config.

Three skills ship a `check_pdf.py` and two ship a `make_pdf.py`, all under
those same bare names, so every conftest also evicts a cached module whose
`__file__` is not its own -- otherwise the suite that collects first
(`tests/architecture_study/`, alphabetically) would hand its copies to the
others, and the failure can be silently green rather than loud. Each suite
asserts the provenance of what it imported for the same reason. Run the whole
`tests/` directory or one suite at a time; naming two suite directories on one
command line is unsupported, because both conftests then load before any test
module is imported and there is nothing cached for the eviction to catch. The
full analysis is in `tests/implementation_study/conftest.py`.

The render tests -- `test_renders_a_tiny_markdown_to_pdf`,
`test_footnotes_render_as_a_notes_chapter`,
`test_a_conforming_report_passes_every_check` -- need pandoc and Chrome
present in the container. Chrome does not survive `./teardown.sh` or an image
upgrade -- reinstall with `gpu_docker/install-chrome.sh`.

Before pushing a manifest change, run both (from the repo root, on the host):

```bash
claude plugin validate .
claude plugin details <bundle>     # skill count must match the manifest
```

`validate` checks schema only -- it accepts a `skills` entry pointing at a
directory that does not exist, and such a skill is dropped *silently* at
install time. `details` is the only thing that catches that typo.

## Architecture

### Bundling is manifest-only

`.claude-plugin/marketplace.json` is the sole manifest -- there is deliberately
no `plugin.json`, because a marketplace entry with `"source": "./"`, its own
`skills` array, and a `version` is a complete plugin definition (without
`version`, Claude Code reports the commit SHA instead).

Skills live flat under `skills/`; nothing on disk records bundle membership.
Re-bundle by editing the `skills` array, **never** by moving a skill directory
-- that breaks the relative links between a `SKILL.md` and its companion files.
Bundles are the installation unit, so split by what someone would want without
the rest: every installed skill's description costs context in every session.

### Skill anatomy

- `SKILL.md` frontmatter is `name` + `description`. The description is the
  trigger -- it is all Claude sees when deciding whether to fire, so it names
  concrete phrasings and states where the skill degrades.
- `disable-model-invocation: true` marks a skill as user-invoked only
  (`/pr-review-draft`, `/pr-review-dossier`, `/implementation-study`,
  `/architecture-study`); its description becomes human-facing rather than a
  trigger, and costs no context. `pr-explain`, `asm-tutorial`, and
  `kernel-perf` omit it and fire automatically.
- Companion `.md` files (`analysis.md`, `writing.md`, `render.md`,
  `diagrams.md`, ...) are read on demand, one per phase or topic, to keep the
  always-loaded `SKILL.md` small.
- Every skill resolves its own directory at runtime (`${CLAUDE_PLUGIN_ROOT}/skills/<name>`,
  falling back to where the file was read from) and defers to the project's
  own command wrapper -- never a bare `python3` -- because the toolchain may be
  containerized.

### asm-tutorial: a four-phase pipeline with cross-file contracts

`SKILL.md` is the spine; each phase has its own reference doc and, mostly, its
own script: Analyze (`analysis.md`, `annotate_asm.py`) -> Write (`writing.md`)
-> Render (`rendering.md`, `make_pdf.py` + `tutorial.css`) -> Verify
(`verification.md`, `check_pdf.py`). A Phase 4 finding loops back to **Phase 2**
(fix the markdown or the CSS), not Phase 3.

Several couplings span files and will break silently if edited one-sidedly:

- `writing.md`'s heading and cross-reference conventions (`## N. Title`,
  "section N") exist to match `check_pdf.py`'s `HEADING_RE` and `XREF_RE`.
- `rendering.md`'s code-sizing inequality ties `tutorial.css`'s `pre`
  font-size to `make_pdf.py`'s `MARGIN_X` and the document's longest code line.
  Changing a margin reflows every page.
- `cdna-facts.md` is the human-checkable mirror of `annotate_asm.py`'s `ARCH`
  table; `test_cdna_facts.py` asserts every `ARCH` key has a section there.
- `test_reference_docs.py` and `test_skill_md.py` assert specific sentences and
  every `<skill-dir>/...` reference in the prose. Rewording a rule can fail the
  suite -- that is intentional, the tests pin the invariants.

The skill's discipline is "derive or cite, never guess": every asserted number
goes in a fact ledger (`<doc>.notes.md`) with a source before it reaches the
prose. Missing inputs cause **omission, never estimation** -- no `.resources`
sidecar means the occupancy section is dropped, and an architecture without
sourced constants (today: gfx90a, gfx950) gets instruction commentary with no
MFMA-cost or occupancy claims. Adding an architecture means sourcing the
constant, cross-checking it against a real listing, documenting the arithmetic
in `cdna-facts.md`, *then* adding the `ARCH` entry.

### code-study: two deliberate forks, one discipline

`implementation-study` studies one algorithm (`path/to/file:symbol`);
`architecture-study` studies a whole system (a directory). Both run a phased
pipeline into a diagram-first verified PDF, and both enforce "cite, derive, or
omit" through a ledger in `<stem>_*.notes.md` that `check_evidence.py` checks
mechanically.

They are **forks, not a shared library**. `make_pdf.py`, `tutorial.css`,
`check_pdf.py`, and `check_evidence.py` exist as separate copies in each skill
directory, so either can be vendored alone; the cost is that a fix to one is
not a fix to the other. Decide consciously which copies a change belongs in,
and say so in the commit message.

What differs beyond scope:

- `architecture-study` has six phases (Survey -> Trace -> Weigh -> Write ->
  Render -> Verify) and a **fixed seven-section spine** matched verbatim by
  `check_pdf.py`'s `SPINE`. `implementation-study` has five phases and a
  five-section spine enforced only by prose.
- `architecture-study` runs nothing -- no experiments, no `measure:` evidence
  class. A claim needing a benchmark becomes one of its closing questions.
  `implementation-study` runs approved experiments and has `experiments.md`.
- Its central rule is the **witness rule**: a paradigm, contract, constraint,
  or coupling reaches the report only with the code structure that
  instantiates it, cited to `path:line`. Section 5 exists to attract "Python
  has a GIL"-class claims that are true of the world and say nothing about the
  system; the rule is what stops them.

Its cross-file couplings, all pinned by `tests/architecture_study/`:

- `check_pdf.py`'s `SPINE`, `BACK_MATTER`, `REQUIRED_DIAGRAMS`,
  `DECISION_MARKERS`, `MIN_QUESTIONS`/`MAX_QUESTIONS`, and
  `PSEUDOCODE_MAX_STEPS` are each restated in `writing.md` or `diagrams.md`.
  `test_reference_docs.py` compares the two ends, so rewording a section title
  in prose without changing the constant fails the suite.
- The abbreviation contract (`GIL (Global Interpreter Lock)[^gil]`, expanded
  once, footnote defined once and used) lives in `check_pdf.py`'s
  `glossary_problems` and in `writing.md`. Never bracket an acronym in prose:
  `check_evidence.py` reads `[BRACKETED-UPPERCASE]` as a ledger citation.
- `tutorial.css` styles the endnote chapter on `.footnotes` with no element
  name, because pandoc emits `<section>` before 3.x and `<aside>` after; an
  element-qualified selector stops applying across that upgrade and the
  chapter renders untitled with no error anywhere.

### pr-review-kit: context first, publish last

Three skills meant to chain: `pr-explain` (read-only briefing, traces blast
radius beyond the diff) -> `pr-review-draft` (wrapper that runs the briefing,
delegates the actual review to *your project's* `pr-review` skill, and submits
as a GitHub pending review) -> `pr-review-dossier` (read-only; builds a
printable PDF case file with form fields, then applies the marked-up PDF's
decisions).

`pr-review-draft` deliberately ships no review standards of its own -- if no
`pr-review` skill is available it stops rather than substituting a generic
review. Nothing reaches a PR author by accident: drafts stay pending,
approving a comment's *wording* is a separate question from approving its
*publication*, and a bare "looks good" never publishes.

`pdf_forms.py` is pure standard library on purpose (no pypdf, reportlab, or
weasyprint) so `pr-review-dossier` stays zero-install beyond Chrome and Python.
`asm-tutorial` is the deliberate exception: it needs pandoc and poppler, and
that is a property of that one skill, not a rule for the repo.

## Conventions

- **Every tracked file is ASCII.** Use `--` for dashes, straight quotes. Tests
  enforce this for `asm-tutorial`'s, `implementation-study`'s, and
  `architecture-study`'s docs; the rest of the repo follows it too.
- Prose in skills explains *why* a mechanism exists, not just what it does --
  the "Why this pipeline and not something simpler" sections are load-bearing,
  because a future editor who does not know why Chrome is driven over CDP
  rather than `--print-to-pdf` will simplify it back into a bug.
- Development runs through the superpowers SDD workflow; `.superpowers/sdd/`
  holds per-task briefs, reports, and review diffs and is entirely git-ignored.
