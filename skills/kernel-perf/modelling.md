# Modelling before coding

Three things compute on paper and are expensive to discover by building: LDS
bank conflicts, occupancy, and the intensity/quantisation trade. Constants here
are gfx942 (CDNA3); the arithmetic carries to gfx90a and gfx950 with their own
numbers.

## LDS banking

LDS is 32 banks x 4 B and retires 128 B per cycle. An access of `W` bytes per
lane is therefore served **128/W lanes at a time**, and those lanes are
consecutive. A group is conflict-free when its dwords cover 32 distinct banks;
if any bank is asked for `n` distinct dwords, the group costs `n` cycles.

That grouping is the part worth internalising, because it makes the answer
depend on the access width:

| access | lanes per cycle | ideal cycles for wave64 |
|---|---|---|
| `ds_read_b32` | 32 | 2 |
| `ds_read_b64` | 16 | 4 |
| `ds_read_b128` | 8 | 8 |

`bank_model.py` computes this for any address function. Run it before choosing
a row stride, not after measuring a slow kernel.

### The row-stride trap

A tile stored with a power-of-two row stride puts every row on the same banks.
The worst case is a stride of exactly half the bank array (64 B): sixteen lanes
land on two bank pairs, an 8x conflict, and nothing in the source hints at it.

Padding fixes the read and can break the write, because reads and writes group
lanes differently. Both constraints have to be solved together:

- a b64 read wants the row stride, in dwords, congruent to 2 mod 4
- a b128 write wants each 8-lane group to span rows that start half a bank row
  apart

When padding cannot satisfy both, two other levers exist. **Permute which row
each thread stages** -- that changes the write pattern while leaving the data
layout, and therefore the reads, untouched. Or **swizzle the layout**: pack
rows into 128 B lines and XOR the slot index with the line index, which is
dense (no padding) and can be made conflict-free both ways. Swizzling costs an
XOR per access and forbids library load helpers that assume constant stride, so
it pays only when the padding it saves buys something else.

## Occupancy

Waves per SIMD is the minimum over independent limiters, and which one binds
changes per configuration:

```
by registers:  floor(512 / VGPRs_per_lane)
by LDS:        floor(LDS_per_CU / LDS_per_block) * waves_per_block / 4
```

with 512 registers per lane per SIMD and 64 KB of LDS per CU on gfx942.

Two consequences worth holding:

**The accumulator sets the register floor.** A wave tile of `WM x WN` costs
`WM*WN/64` registers for accumulators alone, before fragments, addresses or
prefetch. Wanting 4 waves/SIMD means 128 registers a lane, which caps the wave
tile at 64x64 -- so occupancy targets translate directly into tile shapes.

**Tuning constants that trade against registers must be per-configuration.** A
global prefetch depth that suits one tile will spill another, and the spilled
one looks architecturally slow rather than mistuned.

## The three-way trade

Tile choice moves three quantities that pull against each other:

- **Arithmetic intensity** -- FLOP per byte of LDS traffic. Rises with wave
  tile area.
- **Quantisation** -- `blocks / (ceil(blocks/CUs) * CUs)`. Rises as tiles get
  smaller and the grid gets deeper.
- **Occupancy** -- falls as the wave tile grows, via the accumulator.

A change that improves one usually gives it back on another, which is why
single-axis sweeps so often land flat. Compute all three for a candidate before
building it, and expect a win only when a candidate improves one without paying
on the others -- for example a shape that keeps the wave tile and so the
occupancy, while making the grid deeper.

## Roofline

Peak FLOP/s is `CUs * FLOP_per_clk_per_CU * measured_clock`. Both ends need
care: the clock under sustained MFMA load is frequently well below boost, and
the per-CU constant is architectural. On gfx942, `v_mfma_f32_16x16x16f16` is
8192 FLOP over 16 cycles per Matrix Core with 4 per CU, so 2048 FLOP/clk/CU;
bf16 runs at the same rate.

Check the constant from above: no kernel should exceed it, and the best one
should approach it. A measurement that beats the roofline means the roofline is
wrong.

Memory peak deserves the same treatment. Measure the streaming rate past the
last-level cache, and note the cache size -- a benchmark whose working set fits
in it is not measuring DRAM, and its GB/s figure is against the wrong roof.
