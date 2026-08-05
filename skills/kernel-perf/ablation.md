# Building the ablation harness

Two pieces: a way to build the kernel with one path removed, and a way to time
a kernel that computes the wrong answer.

## Compiling a path away

The switch has to be **compile-time**, and it has to come from outside the
source, so one source serves every rung and no edit is needed between
measurements. A runtime flag is not an ablation: it leaves the branch, usually
leaves the loads that feed it, and times a kernel you did not mean to measure.

Every stack has the mechanism; only the spelling changes.

HIP, C++, CUDA -- the preprocessor, driven by `-D`:

```c++
#ifndef ABLATE_STAGE
    store_lds(next_stage, regs);
    load_global(A, ..., regs);
#endif
```

Triton -- a `tl.constexpr` parameter. Each value is a separate specialisation,
so the dead path is gone before codegen rather than predicated at runtime:

```python
@triton.jit
def kernel(..., ABLATE_STAGE: tl.constexpr):
    if not ABLATE_STAGE:
        tl.store(...)
```

The same shape works in any DSL that specialises on a compile-time constant --
a CK template parameter, a CuTe DSL `constexpr`, a Mojo parameter.

Getting the switch in from outside can be the fiddly part. If the build script
does not forward extra flags, a two-line wrapper around the compiler is usually
the shortest path:

```bash
#!/usr/bin/env bash
exec /opt/rocm/bin/hipcc "$@" $EXTRA_FLAGS
```

and then `EXTRA_FLAGS=-DABLATE_STAGE CXX=./wrapper ./build.sh`. For a JIT'd
kernel there is nothing to rebuild, so read the constant from the environment
at the call site and select the rung the same way.

Removing a path can leave variables unused and loops empty. Keep the
surrounding control flow's shape -- `(void)i;` in C++, `pass` in Python --
rather than deleting the loop, so the comparison stays honest.

## Timing without correctness

The project's benchmark almost certainly validates before it times, and will
report an ablated kernel as WRONG and skip it. A separate timing harness that
loads the built artifact, runs it, and reports the median is a few dozen lines
and pays for itself immediately:

```python
for _ in range(5):
    call()                       # warm up
torch.cuda.synchronize()
ev = [(torch.cuda.Event(True), torch.cuda.Event(True)) for _ in range(n)]
for s, e in ev:
    s.record(); call(); e.record()
torch.cuda.synchronize()
ms = sorted(s.elapsed_time(e) for s, e in ev)[n // 2]
```

Median, not mean: a shared GPU produces occasional outliers that a mean will
absorb and a median will reject.

## Keeping ablations honest

**Ablate the path, keep its shape.** Removing a barrier alongside the reads it
guards measures two changes at once. Take one thing out per rung.

**Watch for the compiler removing more than you did.** With the loads gone, an
accumulator may become provably constant and the whole loop may vanish. A
result that is suspiciously fast is usually this. Check the instruction counts
in the generated assembly before believing a rung -- `-S --offload-device-only`
from hipcc, `kernel.asm["amdgcn"]` on Triton's compiled handle.

**Ablation removes bandwidth *and* the instructions that requested it.** A rung
that deletes the staging store also deletes the register round-trip and the
waitcnt chaining it. So a floor bounds an optimisation that removes all of
that; an optimisation that removes only the instructions lands above the floor.
Say which kind you are proposing.

## Reading the ladder

Rungs sum to the runtime. When they do not, the missing time is a real cost you
have not named yet -- launch overhead, tail effects, or a path you forgot to
count.

Convert each delta to a ratio against the target before deciding what to work
on. A rung worth 20% of the kernel is worth nothing if the floor beneath it is
already past the target.
