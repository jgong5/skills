---
name: kernel-perf
description: Optimise an AMD GPU compute kernel by ablation -- delete one path at a time, time what is left, and let the deltas localise the bottleneck. Use when a HIP, rocWMMA, Composable Kernel or Triton kernel on CDNA (gfx90a, gfx942, gfx950) is slower than expected, when asked to tune or profile one, or to judge whether a kernel has reached its ceiling.
---

# kernel-perf

A slow kernel has one dominant cost at a time, and it is rarely the one the
source suggests. This skill finds it by **ablation**: delete a path, time what
is left, and read the delta. An ablated kernel computes garbage -- that is
fine, the number is the point.

Architectures: CDNA (gfx90a, gfx942, gfx950), wave64, MFMA. The method is
architecture-independent; the constants in `modelling.md` are gfx942's.

## Paths used below

`<skill-dir>` is this skill's own directory: `${CLAUDE_PLUGIN_ROOT}/skills/kernel-perf`
if that exists, otherwise the directory this file was read from. Run scripts
through the project's own command wrapper (often a container shell), never a
bare `python3`.

## The loop

### 1. Get a tight loop

One command that rebuilds and prints a time. Under a minute, or the rest of
this is unaffordable.

Give it a correctness-free mode: ablated kernels produce wrong answers, so a
harness that validates before timing will refuse to time them. See
`<skill-dir>/ablation.md`.

**Done when** one command prints times for the shapes you care about, and two
consecutive runs on an otherwise idle GPU agree within 2%. That 2% is your
noise floor; changes smaller than it are not results.

### 2. Anchor the roofline

Measure peak on this part rather than quoting the family's spec sheet -- clocks
under sustained MFMA load are often far below boost, and the gap silently
rescales every percentage you will report.

**Done when** you can state the kernel's percent of a peak you measured, and
the clock that peak was measured at.

### 3. Ablate until the runtime is accounted for

Remove one path, rebuild, time. Each removal yields a **floor**: the time with
that path free. A floor bounds what optimising that path can ever win, so a
floor above your target retires the whole idea before you build it.

Ladder for a tiled GEMM-like kernel, each rung adding one path back:

| rung | what it isolates |
|---|---|
| math only (no memory, no epilogue) | tile quantisation and issue limits |
| + operand reads from LDS | LDS read cost and how well it hides |
| + epilogue | output-path cost |
| + global loads and LDS writes | the staging pipeline |

**Done when** every rung's delta is attributed to a named cost, and the rungs
sum to the full kernel time.

### 4. Record resources with every number

Read the compiler's own report (`-Rpass-analysis=kernel-resource-usage`) for
registers, spill count, LDS bytes and occupancy. A configuration that measures
far worse than its neighbours has usually **spilled**, and a spill reads
exactly like an architectural limit until you look.

**Done when** every configuration in your results table carries its spill count
and occupancy beside its time.

### 5. Model the fix, then land it alone

Predict the change numerically before writing it -- bank conflicts, occupancy,
bytes per FLOP all compute on paper. `<skill-dir>/modelling.md` has the
arithmetic and `<skill-dir>/bank_model.py` runs the LDS part.

**Done when** the change was predicted, then measured on its own, and the
measurement is outside the noise floor from step 1.

## Before reporting a ceiling

A floor measured with an axis **pinned** is not a ceiling. An axis is pinned
when every configuration you measured shares one value for it.

This is the failure this skill exists to prevent. In the work it came from,
three separate "this is structural" conclusions were each overturned by moving
one pinned axis:

| pinned axis | conclusion drawn | after moving it |
|---|---|---|
| blocks per CU, always 1 | operand reads cost 1.14x and cannot be removed | 0.94x at twice the occupancy |
| prefetch depth, one global constant | this tile is 2.3x slower, discard it | fastest tile in the kernel |
| tile shape, one family | quantisation is the limit | five families land within 0.5% |

**Done when** you have listed the axes you varied and the axes that stayed
fixed, and either moved each pinned axis or named it as untested.

Axes worth varying: tile shape, waves per block, blocks per CU, prefetch depth,
data layout, and the loop structure itself.

A flat result -- several configurations spanning wide ranges of an axis all
landing within noise -- is a finding, not a failure. It says the binding
constraint is not on that axis, which is worth more than another point estimate.

## Signatures worth knowing

| symptom | cause to check first |
|---|---|
| one configuration far off its neighbours | register spill; read `VGPRs Spill` |
| a tuning constant that is global | it hides wins on configs wanting another value; make it per-config |
| LDS row stride is a power of two | bank conflicts; run `bank_model.py` |
| accumulator moves in the hot loop | a branch split the block and evicted them; make the loop branch-free |
| hand-written scheduling hints | measure against no hints, the compiler often wins |
| profiler counters that will not reconcile | use ratios within one counter pair; absolutes aggregate over units you cannot see |
| a result that changes between runs | another process on the GPU, including your own background job |
| a rebuild that changes nothing | the running process still holds the old mapping; relaunch it |
| behaviour a library documents as unspecified | probe it on this target and pin the result in a test |

## Profilers

`rocprofv3` counter collection earns its place on one question: whether LDS
bank conflicts dominate (`SQ_LDS_BANK_CONFLICT / SQ_LDS_IDX_ACTIVE`). That
ratio is trustworthy and hard to get any other way.

Treat its absolute values as unitless. They aggregate over shader engines and
SIMDs in ways that will not divide into your hand arithmetic, and reconciling
them is a sink. Ablation answers "what does this path cost" directly, in
wall-clock, which is usually the question you actually have.

For per-instruction stall attribution, reach for instruction tracing (ATT)
early rather than inferring stalls from ablation deltas.
