# Phase 1 -- Analyze

Read this before touching the assembly.

## Resolve inputs

You are given one `.s` path. Everything else is discovered:

- **Source file.** Look for a same-stem source near the `.s` (`.hip`, `.cpp`,
  `.cu`) by walking up from the `.s`'s directory toward the project root, and
  by grepping the listing's `.amdhsa_kernel` names for a recognizable
  identifier to search for in the tree. If nothing turns up, proceed without
  one -- the assembly is still explainable, but every "why does the source do
  this" claim gets marked `(inferred)` instead of traced to a line.
- **`.resources` sidecar.** Same stem, `.resources` extension, next to the
  `.s`. If absent, the register-budget and occupancy sections of the tutorial
  are omitted outright -- never estimated. `annotate_asm.py`'s
  `read_resources()` already knows this format if you want to inspect it
  directly rather than reading the sidecar by eye.
- **Annotation.** If the `.s` has no end-of-line comments yet, annotate it
  first:

      ./shell.sh python3 /workspace/skills/skills/asm-tutorial/annotate_asm.py <in.s>

  This also reports the detected architecture and warns if it is not one
  `annotate_asm.py`'s `ARCH` table knows (see `cdna-facts.md`).

## Build the fact ledger

Before writing a word of prose, create `<doc>.notes.md` beside where the
tutorial will land (see the output-path rule in `writing.md`). For every
number the tutorial will eventually assert, add a line:

    <number>  <what it is>  <source>

where `<source>` is one of:

- a line number in the `.s` or the source file (`asm:142`, `src:67`)
- a key in the `.resources` sidecar (`.resources: VGPRs`)
- an entry in `cdna-facts.md` (`cdna-facts.md: gfx942 flop_per_clk_per_matrix_core`)
- `derived from <other ledger line(s)>`, with the arithmetic spelled out

A number with no ledger line does not go in the tutorial. This is the
mechanism behind the skill's one hard rule -- derive or cite, never guess --
and it is what makes Phase 4's verification pass mechanical instead of a
re-read of the whole document: every assertion already has a paper trail.

Leave the ledger in place after the run. It is the audit trail for the
tutorial that follows it, and it makes a later revision of the same document
resumable without re-deriving everything from scratch.

## Read the program structure

Walk the listing once, end to end, and note its actual sections -- prologue,
address setup, prefetch, main loop, epilogue, whatever this kernel has. This
determines the body's section breaks in `writing.md`; do not force a shape
the kernel does not have (a kernel with no LDS gets no LDS section).
