---
name: asm-tutorial
description: Turn an annotated AMD CDNA GPU assembly listing (.s) into a verified PDF tutorial that walks the listing against its source, with every register, LDS, and occupancy number traced to a source or citation. Use when asked to explain, document, or produce a tutorial/walkthrough/PDF for GCN assembly output -- especially rocWMMA or Composable Kernel kernels -- on gfx90a, gfx942, or gfx950. Degrades to generic instruction commentary on other targets.
---

# asm-tutorial

Turns one `.s` file into a verified PDF tutorial in four phases: analyze the
listing against its source, write a tutorial with a fixed spine, render it to
PDF, verify the render. Architectures: the CDNA family (gfx90a, gfx942,
gfx950) -- wave64, MFMA-based. An unrecognized target still gets instruction
comments, just no MFMA cost or occupancy claims.

## Paths used below

`<skill-dir>` is this skill's own directory. Resolve it in this order:

1. `${CLAUDE_PLUGIN_ROOT}/skills/asm-tutorial`, if that path exists (this is
   where a plugin *install* copies the bundle -- outside any bind mount a
   container-based toolchain might have).
2. Otherwise, the directory this file is read from.

Before running any script below, confirm `<skill-dir>` is reachable by the
toolchain that will run `python3` (for example, `./shell.sh ls <skill-dir>`
if the project's own instructions route commands through a container). If it
is not, copy `<skill-dir>` into a directory that toolchain can reach, and use
that copy as `<skill-dir>` for the rest of this run.

`<scratch>` is `<dir>/docs/`, the same directory the tutorial markdown lands
in (see `writing.md`'s Output path section) -- the fact ledger
(`<doc>.notes.md`) lives there too.

## The four phases

1. **Analyze** -- read `<skill-dir>/analysis.md`, then resolve inputs and
   build the fact ledger.
2. **Write** -- read `<skill-dir>/writing.md`, then write `<doc>.md`.
3. **Render** -- read `<skill-dir>/rendering.md`, then run
   `<skill-dir>/make_pdf.py <doc>.md`.
4. **Verify** -- read `<skill-dir>/verification.md`, then run
   `<skill-dir>/check_pdf.py <doc>.pdf <doc>.md`. A finding sends you back to
   Phase 2, not Phase 3 -- `verification.md` explains why.

If the `.s` is not yet annotated (no end-of-line comments), Phase 1 starts
with `<skill-dir>/annotate_asm.py <in.s>`. Per-architecture constants it uses
are documented, with their sources, in `<skill-dir>/cdna-facts.md`.

## Checklist

- [ ] Fact ledger (`<doc>.notes.md`) written, every asserted number tagged
      with its source
- [ ] Tutorial covers the fixed spine (compute + shape, tiling, register/LDS
      budget, occupancy as a minimum over limiters, compiler resource report
      reconciled against the budget) before the derived, program-order body
- [ ] Every numbered section and every "section N" cross-reference checked
- [ ] `<skill-dir>/make_pdf.py <doc>.md` produced `<doc>.pdf`
- [ ] `<skill-dir>/check_pdf.py <doc>.pdf <doc>.md` reports no problems
- [ ] Six sample pages it names have had an actual look, not just the
      mechanical checks

## Degradation

| Missing | Behavior |
| --- | --- |
| source file | assembly is explained; "why" claims marked `(inferred)` |
| `.resources` sidecar | occupancy and register-budget sections omitted, not estimated |
| unrecognized arch | generic instruction comments; no MFMA cost, no occupancy |
| Chrome | stop; point at the project's own Chrome-install script if it has one |
| pandoc | stop; it is expected to already be present, so its absence means something else is wrong |

## Requirements

- Python 3 (standard library, plus `websockets` for `make_pdf.py`)
- `pandoc`
- `google-chrome`, `google-chrome-stable`, `chromium`, or `chromium-browser`
- `poppler-utils` (`pdftotext`, `pdffonts`, `pdftoppm`, `pdfinfo`)

Run every script the way the project's own instructions specify -- if a
`CLAUDE.md` or similar mandates a wrapper (e.g. a containerized `python3`),
use it rather than the bare interpreter.
