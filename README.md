# jgong5's Claude Code skills

Three independent plugin bundles, installed separately. See each bundle's own
section for what it does and how to install it.

| Bundle | Skills | What it's for |
| --- | --- | --- |
| [`pr-review-kit`](#pr-review-kit) | `pr-explain`, `pr-review-draft`, `pr-review-dossier` | Context-first pull-request review |
| [`amd-gpu`](#amd-gpu) | `asm-tutorial` | Turn AMD CDNA GPU assembly into a verified PDF tutorial |
| [`implementation-study`](#implementation-study) | `implementation-study` | Turn one algorithm implementation into an evidence-grounded, verified PDF study |

## pr-review-kit

Claude Code skills for reviewing pull requests **context-first**: understand the
change's blast radius before reading a line of it, keep the review private until
you have judged every comment, and publish only on an explicit say-so.

The three skills are designed to be used in order, but each works alone.

| Skill | Invocation | What it does |
| --- | --- | --- |
| `pr-explain` | automatic, or ask to "explain this PR" | Turns a PR into a reviewer briefing: why it exists, what it touches beyond the diff, and two plain-ASCII diagrams (architecture and data/control flow) that render in any terminal. Read-only. |
| `pr-review-draft` | `/pr-review-draft` | Runs a `pr-explain` briefing, delegates the review itself to your installed `pr-review` skill, then submits findings as a GitHub **pending** review that stays private until you click Submit. Publishes only when you explicitly ask. |
| `pr-review-dossier` | `/pr-review-dossier` | Builds a printable PDF case file for the drafted comments: each one with the code it points at, the precedent behind it, the failure scenario, and a Confirmed/Speculative/Refuted verdict, plus tick-boxes for Publish / Reword / Drop and a typable reword note. Hand the marked-up PDF back and it applies your decisions. |

Why the split: a diff can be read locally, but its interactions cannot, and a
review comment that looks sharp in chat often rests on nothing once you go
looking for the precedent. `pr-explain` supplies the interactions; the dossier
forces every comment to show its evidence before it reaches the author.

### Install

In Claude Code:

```
/plugin marketplace add jgong5/skills
/plugin install pr-review-kit@jgong5
```

Or from your shell:

```bash
claude plugin marketplace add jgong5/skills
claude plugin install pr-review-kit@jgong5
```

Restart Claude Code (or start a new session) for the skills to load. Confirm
with `claude plugin list`, or by typing `/pr-review-draft` and seeing it resolve.

### Requirements

- **[`gh`](https://cli.github.com/), authenticated** (`gh auth login`) -- all
  three skills read PRs through it, and `pr-review-draft` writes through it.
- **A `pr-review` skill**, for `pr-review-draft` only. This kit deliberately does
  not ship one. `pr-review-draft` is a wrapper that adds context up front and
  draft-safety at the end; the review standards themselves belong to your
  project, and many repositories ship their own `pr-review` under
  `.claude/skills/pr-review/`. Without one available, `pr-review-draft` stops
  rather than substituting a generic review.
- **Chrome or Edge, and Python 3**, for `pr-review-dossier` only. The PDF route
  is deliberately zero-install: a self-contained HTML file printed by headless
  Chrome, then post-processed by `pdf_forms.py`, which is pure standard library.
  No pandoc, reportlab, weasyprint, or pypdf needed.

Nothing here is tied to a particular language or project. `pr-review-dossier`'s
`example.html` is rendered from a real PyTorch PR, included only as a layout and
density reference for the generated pages.

### Safety model

These skills are built so that nothing reaches a PR author by accident.

- `pr-explain` and `pr-review-dossier` never write to GitHub at all.
- `pr-review-draft` posts only when asked, and posts a **draft** by default.
  Approving a comment's *wording* is treated as a separate question from
  approving its *publication* -- a bare "looks good" never escalates a draft
  into a published review.
- Before any write to GitHub, the exact review body and every inline comment are
  shown for explicit approval, and every posted comment is marked as
  AI-generated. If your repository has its own AI-contribution policy
  (`AI_POLICY.md`, `CONTRIBUTING.md`), the skill reads and complies with it too.

## amd-gpu

### asm-tutorial

Turns an AMD CDNA GPU assembly listing (`.s`) into a verified PDF tutorial:
analyze the listing against its source, write a tutorial with a fixed spine
(what the kernel computes, tiling, register/LDS budget, occupancy, the
compiler's own resource report), render it to PDF, then verify the render --
mechanically over every page (embedded fonts, no wrapped code lines, every
cross-reference resolves) plus a sampled visual look at six representative
pages.

Architectures: the CDNA family -- gfx90a, gfx942, gfx950 -- which share a
wave64 execution model and an MFMA lineage. Only gfx942 currently has sourced
MFMA-cost and occupancy constants; gfx90a and gfx950 take the same degraded
path as any unrecognized target -- instruction commentary only, no MFMA cost
or occupancy claims -- until their own constants are sourced. Per-architecture
constants and their sources are in `skills/asm-tutorial/cdna-facts.md`.

### Install

```
/plugin marketplace add jgong5/skills
/plugin install amd-gpu@jgong5
```

Or from your shell:

```bash
claude plugin marketplace add jgong5/skills
claude plugin install amd-gpu@jgong5
```

### Requirements

- Python 3 (standard library, plus `websockets` for the PDF-render step)
- `pandoc`
- `google-chrome-stable` (or another Chromium-family binary)
- `poppler-utils` (`pdftotext`, `pdffonts`, `pdftoppm`, `pdfinfo`)

Unlike `pr-review-dossier` above, this skill's PDF route is not zero-install:
a tutorial this dense in 100-column assembly needs pandoc's markdown handling
and a real print stylesheet, which is worth the extra dependencies for this
one skill. That is a property of `asm-tutorial`, not a rule for this repo.

## implementation-study

Turns one algorithm implementation into a study document and a verified PDF:
what it computes, where it sits, why each choice was made rather than the
alternatives it beat, and what would have to be true for a different choice
to win.

```
/implementation-study path/to/file.py:symbol
```

The argument is one entry point -- `path/to/file:symbol`, or `path/to/file`
when the file is the unit. Anything vaguer (a bare symbol name, a directory,
"the queue implementation") is not a resolved entry point, and the skill asks
rather than guessing.

Five phases run in order, each reading only its own reference doc:

| Phase | What it does |
| --- | --- |
| Analyze | Resolves the boundary, the contract, and the caller map; opens the comprehension ledger; records the integrity baseline the last phase checks against. |
| Investigate | Turns the ledger into a decision inventory -- the implementation's choices, their realistic alternatives, and the trade-off between them. Proposes an experiment only when a trade-off cannot be settled by reasoning. |
| Write | Turns the ledger and the inventory into the study document: a fixed five-section spine, a middle shaped by the code's own structure, decision blocks, and back matter. Discovers nothing new. |
| Render | Turns the markdown into a PDF through pandoc and headless Chrome, classifying any overlong code line before touching the stylesheet. |
| Verify | The gate: mechanical PDF checks, a mechanical evidence check, and a manual read-through, with every finding routed back to the phase that caused it. |

Outputs land next to the code, in the nearest ancestor `docs/` directory found
without crossing the repository boundary -- an ancestor `docs/` outside the
repository is never a candidate, no matter how close it sits -- or, with the
user's explicit approval, the entry point's own directory if no `docs/`
exists inside the repository, provided that directory is
not the repository root itself -- an entry point at the root with no `docs/`
above it makes the skill stop and ask for an output subdirectory rather than
write to the root): the study document
`<stem>_study.md`, the comprehension ledger `<stem>_study.notes.md`, any
approved experiment scripts and their captured output under
`<stem>_study_experiments/`, and the rendered `<stem>_study.pdf`. Every one
of those paths must be new -- the skill creates files and never overwrites
one.

The rule the whole pipeline exists to enforce: every substantive claim is
**cited** to a specific line of the code under study, **derived** from
something already cited, **measured** by an approved experiment, or
**omitted**. Nothing is estimated to fill a gap. That shows up in the
document as ledger IDs behind the prose, as decision blocks that must state
the alternatives and the trade-off rather than only the choice, and as an
Improvements chapter whose every entry is falsifiable -- a reader can go
check the stated condition and find it false.

### Safety model

- **The repository under study is read-only.** The skill writes only inside
  the output paths above, and the final phase checks that mechanically: a
  clean `git status` against the baseline the first phase recorded, or a file
  snapshot comparison when the repository is not a git work tree. A phase
  that wants to reformat or "just quickly fix" something in the code under
  study has left the skill's scope. The git check covers what `git status`
  covers -- no tracked file changed, and nothing untracked appeared outside
  the output directory -- which does not extend to paths `.gitignore`
  excludes. That gap is closed by prevention rather than by a claim: an
  experiment must run with its language's cache and artifact writes
  suppressed (`PYTHONDONTWRITEBYTECODE=1` and the per-language equivalents),
  as part of the wrapper command, so those writes never happen.
- **Experiments run only with explicit approval.** Each one is proposed as a
  single plan line naming the claim it supports, the script, what it
  measures, and its bounds; nothing is written or run until you approve that
  exact line. A declined experiment is recorded as declined, and the claim it
  would have supported is derived from what is already known or dropped.
- **An experiment executes code from the repository under study, and this
  skill adds no sandbox** beyond not writing outside the experiment
  directory: no container, no restricted interpreter, no network isolation.
  Approve one with the same care you would give to running someone else's
  script on your machine, because that is what it is.

### Install

```
/plugin marketplace add jgong5/skills
/plugin install implementation-study@jgong5
```

Or from your shell:

```bash
claude plugin marketplace add jgong5/skills
claude plugin install implementation-study@jgong5
```

### Requirements

- Python 3 (standard library, plus `websockets` for the PDF-render step)
- `pandoc`
- `google-chrome-stable` (or another Chromium-family binary)
- `poppler-utils` (`pdftotext`, `pdffonts`, `pdftoppm`, `pdfinfo`)

Same dependency set as `asm-tutorial`, and for the same reason: a dense
technical document needs pandoc's markdown handling, a real print stylesheet,
and poppler to check what actually came out.

This skill is **user-invoked only** -- it never fires on its own, because a
study is a deliberate, expensive act, not something to start by mentioning a
file. It is language-agnostic: nothing in the pipeline assumes Python, and
the entry point can be any hand-written source file. It stops rather than
studying generated, vendored, or minified code (`vendor/`, `third_party/`,
`node_modules/`, `*.min.*`, or a "do not edit" header) -- code nobody
hand-wrote has no design decisions to recover.

## Update

```
/plugin marketplace update jgong5
/plugin update <bundle>@jgong5
```

where `<bundle>` is `pr-review-kit`, `amd-gpu`, or `implementation-study`.
Same commands work as `claude plugin ...` from the shell. Updates apply on
restart.

Qualify the plugin with `@jgong5` on update. The bare name resolves for
`install` and `details`, but `update` reports `Plugin "<bundle>" not found`
without it.

## Uninstall

```
/plugin uninstall <bundle>@jgong5
/plugin marketplace remove jgong5
```

`marketplace remove` drops all bundles at once, since one marketplace entry
covers this whole repo -- only run it once you want none of them installed.

## Layout

```
.claude-plugin/
  marketplace.json      # the only manifest: defines every bundle in this repo
skills/
  pr-explain/            # SKILL.md + diagrams.md (ASCII diagram recipes)
  pr-review-draft/       # SKILL.md
  pr-review-dossier/     # SKILL.md + render.md, pdf_forms.py, example.html
  asm-tutorial/          # SKILL.md + analysis.md, writing.md, rendering.md,
                         # verification.md, cdna-facts.md, annotate_asm.py,
                         # make_pdf.py, check_pdf.py, tutorial.css
  implementation-study/  # SKILL.md + five phase docs, experiments.md,
                         # make_pdf.py, check_pdf.py, check_evidence.py,
                         # tutorial.css
tests/
  asm_tutorial/          # pytest suite for asm-tutorial's scripts
  implementation_study/  # pytest suite for implementation-study's scripts
                         # and reference docs
```

Skills live flat under `skills/`; nothing on disk records which bundle a skill
belongs to. Grouping is done entirely by the `skills` array of a `plugins[]`
entry in `marketplace.json`, so a skill can be re-bundled by editing the
manifest -- never by moving files, which would break the relative links between
a `SKILL.md` and its companion files.

There is deliberately no `plugin.json`. A marketplace entry with
`"source": "./"` and its own `skills` list is a complete plugin definition, and
it carries `version` too -- without one, Claude Code falls back to reporting the
commit SHA as the installed version.

## Adding to this repo

**A new skill in an existing bundle:** create `skills/<name>/SKILL.md`, then add
`"./skills/<name>"` to that bundle's `skills` array.

**A new bundle:** append another entry to `plugins[]`. It shares `"source": "./"`
with the others and simply names a different subset of `skills/`. A bundle
holding a single skill is perfectly normal. Bundles are the unit of
installation, so split by what someone would want *without* the rest -- every
installed skill's description occupies context in every session, whether or not
it fires.

Bundle names prefix their skills (`<bundle>:<skill>`), so keep them short.

**Before pushing**, confirm the manifest matches reality:

```bash
claude plugin validate .
claude plugin details <bundle>    # skill count must match the manifest
```

Run both. `validate` checks the schema only -- it accepts a `skills` entry
pointing at a directory that does not exist, and such a skill is then dropped
*silently* at install time, with no error and no warning. The inventory printed
by `details` is the only thing that catches a typo there.

## License

MIT -- see [LICENSE](LICENSE).
