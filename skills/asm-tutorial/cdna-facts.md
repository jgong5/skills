# CDNA per-architecture facts

Constants `annotate_asm.py`'s `ARCH` table needs, one entry per row, with the
source for each. `ARCH` is the parser's copy; this file is for a human to
check it against.

## gfx942 (CDNA3, MI300X/MI300A/MI308X)

| Constant | Value | Source |
| --- | --- | --- |
| `wave` | 64 | CDNA is wave64 across the whole family: every wavefront occupies 64 lanes, unlike RDNA's wave32/wave64 choice. |
| `flop_per_clk_per_matrix_core` | 512 | Derived: hgemm_spectrum's compute roofline uses 2048 FLOP/clk/CU for gfx942, and a CU has 4 Matrix Cores, so 2048/4 = 512. Cross-checked against the assembly itself: every `v_mfma_f32_MxNxKx_f16` in the rocWMMA listing satisfies `cycles = 2*M*N*K / 512` for the cycle counts the annotated comments report, e.g. `v_mfma_f32_16x16x16_f16` -> 2*16*16*16 = 8192 FLOP -> 8192/512 = 16 cycles. |

## gfx90a (CDNA2, MI200 series) -- not yet in `ARCH`

Not entered: no FLOP/clk/matrix-core figure has been sourced and cross-checked
against a real listing the way the gfx942 figure was. AMD's own architecture
materials describe CDNA2 as halving each Matrix Core's per-cycle FP16
throughput relative to CDNA3, but "halves" is not a number this file can cite
yet. Until a number is sourced from an ISA or architecture guide and confirmed
against `cycles = 2*M*N*K / flop_per_clk_per_matrix_core` on a real gfx90a
listing, gfx90a stays on `annotate_asm.py`'s unknown-target path: instruction
comments are still produced, but with no MFMA cost or occupancy claim.

To add it: find the CU-level or Matrix-Core-level peak FP16 FLOP/clk figure
in AMD's CDNA2 whitepaper or the MI200 architecture/ISA guide, divide by the
Matrix Cores per CU it states, verify the result reproduces the cycle counts
on a real annotated gfx90a `.s`, then add a row here with the document title,
section, and the arithmetic, and add the entry to `ARCH`.

## gfx950 (CDNA4, MI350 series) -- not yet in `ARCH`

Same status as gfx90a, for the same reason: no sourced-and-cross-checked
figure yet. Follow the same procedure once a gfx950 architecture guide and a
real annotated listing are available to check against.
