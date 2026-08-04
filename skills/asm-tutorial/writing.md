# Phase 2 -- Write

## Two rules that apply to every phase, not just this one

- **Derive or cite, never guess.** If a number is not in the fact ledger from
  Phase 1, mark the claim `(unverified)` rather than asserting it as fact.
- **The assembly is the subject; the source is the cross-check.** Sections
  walk the `.s` and reach back to the source to explain *why*. Never the
  reverse -- this is a tutorial for reading assembly, not a re-explanation of
  the source with assembly as decoration.

## The fixed spine

Every tutorial opens with these, in this order, regardless of what kernel it
covers:

1. **What the kernel computes, and the shape of the problem.** One or two
   paragraphs: the operation (e.g. `D = A @ B`, or `D = A @ B` with a
   split-K atomic epilogue), the datatypes, and the problem shape if it is
   fixed at compile time.
2. **Tiling parameters, traced from the source.** Every tile-shape constant
   (BM/BN/BK, warp tile, per-thread tile) with a citation to the source line
   that sets it, or to the template instantiation that fixes it.
3. **Register and LDS budget.** Table: VGPRs, AGPRs, SGPRs, LDS bytes/block,
   from the `.resources` sidecar via the ledger. Omit this section entirely
   if there is no sidecar -- do not estimate it from the assembly.
4. **Occupancy**, presented as a minimum over limiters, not a single cause.
   State which limiter is binding (registers vs. LDS vs. workgroup size) using
   the compiler's own `Occupancy [waves/SIMD]` figure -- never recompute it
   from the register counts, because occupancy is a joint minimum and
   reimplementing that model independently will occasionally disagree with
   the compiler for reasons a reader cannot see.
5. **The compiler's resource report, reconciled against items 3 and 4.**
   Walk the `.amdhsa_*` kernel-descriptor directives (`.amdhsa_next_free_vgpr`,
   `.amdhsa_next_free_sgpr`, etc.) and show how they relate to the numbers in
   items 3-4 -- including where they *don't* match exactly (e.g. a VGPR
   granule rounding `NumVgprs` up before it becomes `TotalNumVgprs`). A
   mismatch explained is more useful than a round number asserted.

## The derived middle

After the spine, walk the assembly in program order. Section breaks come from
the program structure you identified in Phase 1 -- prologue, address setup,
prefetch, main loop, epilogue -- not from a fixed template. A kernel with no
LDS gets no LDS section.

Within a section, favor explaining representative instructions over every
instruction: if sixteen `v_mfma_f32_16x16x16_f16` in a row do the same thing,
explain the pattern once and note the repeat count, the way
`annotate_asm.py`'s own comment-suppression already does in the annotated
source.

## Output path

Write to `<dir>/docs/<stem>_asm_tutorial.md`, where `<dir>` is the nearest
directory containing a `docs/` subdirectory found by walking up from the
`.s`'s parent. If none is found walking up to the filesystem root, write
beside the `.s` instead.

## Numbered sections and cross-references

Use `## N. Title` for top-level sections (matching `check_pdf.py`'s
`HEADING_RE`), numbered consecutively from 1. When referring to another
section in prose, write "section N" or "sections N and M" exactly (matching
`check_pdf.py`'s `XREF_RE`) -- Phase 4 checks every one of these resolves to a
heading that exists. Renumbering a section means re-checking every reference
to it; this is exactly the defect class that cost the most time on the first
tutorial this skill was generalized from.
