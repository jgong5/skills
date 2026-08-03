---
name: asm-tutorial
description: Turn an annotated AMD CDNA GPU assembly listing (.s) into a PDF tutorial that walks the listing against its source, with traceable register/LDS/occupancy numbers. Use when asked to explain, document, or produce a tutorial/walkthrough for GCN/RDNA assembly output, especially rocWMMA/CK kernels on gfx90a, gfx942, or gfx950.
---

# asm-tutorial

Turns one `.s` file into a verified PDF tutorial: analyze the listing against
its source, write a tutorial with a fixed spine, render it to PDF, verify the
render.

## Paths used below

`<skill-dir>` is this skill's own directory. Resolve it in this order:

1. `${CLAUDE_PLUGIN_ROOT}/skills/asm-tutorial` if that path exists (plugin
   install).
2. Otherwise, the directory containing this file.

If neither is reachable by the toolchain that runs `python3` (for example,
because it resolves to a path outside a container's bind mounts), copy
`<skill-dir>` into a directory the toolchain can reach before continuing, and
use that copy as `<skill-dir>` for the rest of this skill.

## The four phases

1. **Analyze** -- read `analysis.md`, then build the fact ledger.
2. **Write** -- read `writing.md`, then write the tutorial markdown.
3. **Render** -- read `rendering.md`, then run `<skill-dir>/make_pdf.py`.
4. **Verify** -- read `verification.md`, then run `<skill-dir>/check_pdf.py`.

## Checklist

- [ ] Fact ledger written to `<doc>.notes.md`, every number tagged with its source
- [ ] Tutorial covers the fixed spine (compute, tiling, register/LDS budget,
      occupancy, compiler resource report) before the derived, program-order body
- [ ] `<skill-dir>/make_pdf.py <doc>.md` produced a PDF
- [ ] `<skill-dir>/check_pdf.py <doc>.pdf <doc>.md` reports no problems
