# Building the ablation harness

Two pieces: a way to compile the kernel with one path removed, and a way to
time a kernel that computes the wrong answer.

## Compiling a path away

Guard each path with a macro and pass it on the command line, so one source
serves every rung of the ladder and no edit is needed between measurements.

```c++
#ifndef ABLATE_STAGE
    store_lds(next_stage, regs);
    load_global(A, ..., regs);
#endif
```

If the project's build script does not forward extra flags, a two-line wrapper
around the compiler is usually the shortest path:

```bash
#!/usr/bin/env bash
exec /opt/rocm/bin/hipcc "$@" $EXTRA_FLAGS
```

and then `EXTRA_FLAGS=-DABLATE_STAGE CXX=./wrapper ./build.sh`.

Removing a path can leave variables unused and loops empty. Prefer `(void)i;`
over deleting the loop, so the surrounding control flow keeps its shape and the
comparison stays honest.

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
in the generated assembly before believing a rung.

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
