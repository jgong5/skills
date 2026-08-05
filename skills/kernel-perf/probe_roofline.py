#!/usr/bin/env python3
"""Measure this part's ceilings instead of quoting the family's spec sheet.

Three numbers, none of them a lookup:

  * **Compute.** `CUs x FLOP_per_clk_per_CU x clock`, where the clock is
    *sampled under a dense MFMA load* rather than assumed. Boost clocks are not
    what a part sustains under back-to-back GEMMs, and the gap silently
    rescales every percentage you will report.
  * **Memory.** What a streaming kernel actually sustains. A spec-sheet HBM
    figure describes the package; a salvage part with a fraction of the CUs
    cannot saturate a memory system built for the full one.
  * **Cache.** Where the last-level cache knee is. A benchmark whose working
    set sits in a memory-attached last level is not measuring DRAM, and its
    GB/s is against the wrong roof. This cache is often not reported by
    rocminfo or by torch, so the sweep looks for it directly.

    python probe_roofline.py                        # all three
    python probe_roofline.py --what compute --device 1

Needs torch and triton (triton ships with the ROCm PyTorch wheels). `amdsmi`
(ships with ROCm) is needed for the sustained clock; without it the compute
roof is skipped rather than guessed.
"""

import argparse
import statistics
import threading

import torch
import triton
import triton.language as tl

# Dense f16/bf16 MFMA throughput per CU. gfx942: v_mfma_f32_16x16x16f16 is
# 16*16*16*2 = 8192 FLOP over 16 cycles on one Matrix Core = 512 FLOP/clk, and
# there are 4 Matrix Cores per CU. Only gfx942 is verified here; the others
# follow the same arithmetic from published per-CU rates. The cross-check below
# is what catches a wrong constant -- read its output rather than trusting this.
FLOP_PER_CLK_PER_CU = {
    "gfx90a": 1024,   # CDNA2
    "gfx942": 2048,   # CDNA3, verified on MI308X
    "gfx950": 4096,   # CDNA4
}

BLOCK = 8192

# Cache sweep sizes, MiB. Wide enough to bracket both a few-MB L2 and a
# 256 MB memory-attached last level.
CACHE_SIZES_MIB = (32, 64, 128, 192, 256, 320, 384, 512, 1024, 2048, 4096)

# Below this per-call duration the fixed launch cost is a large enough share of
# the measurement to understate the rate, so those rows do not vote on the knee.
MIN_US_FOR_KNEE = 25.0

# The plateau has to beat the asymptote by this much before we call it a cache.
MIN_CACHE_RATIO = 1.15

# How close to the plateau a size must stay to still count as cache-resident.
NEAR_PLATEAU = 0.25


@triton.jit
def _read(P, n, out, BLOCK: tl.constexpr):
    # int64 offsets: 4 GiB of f16 is 2^31 elements, and a default int32 offset
    # silently wraps into a memory access fault.
    pid = tl.program_id(0).to(tl.int64)
    o = pid * BLOCK + tl.arange(0, BLOCK).to(tl.int64)
    tl.store(out + pid, tl.sum(tl.load(P + o, mask=o < n, other=0.0)))


@triton.jit
def _copy(S, D, n, BLOCK: tl.constexpr):
    pid = tl.program_id(0).to(tl.int64)
    o = pid * BLOCK + tl.arange(0, BLOCK).to(tl.int64)
    m = o < n
    tl.store(D + o, tl.load(S + o, mask=m, other=0.0), mask=m)


def arch_of(device: int = 0) -> str:
    """Bare architecture name -- 'gfx942:sramecc+:xnack-' -> 'gfx942'."""
    return torch.cuda.get_device_properties(device).gcnArchName.split(":")[0]


def flop_per_clk(arch: str, override: int | None = None) -> int:
    """Per-CU dense f16/bf16 FLOP/clk, or a clear error naming the fix."""
    if override:
        return override
    if arch not in FLOP_PER_CLK_PER_CU:
        raise KeyError(
            f"no FLOP/clk constant for {arch}; pass --flop-per-clk N "
            f"(known: {', '.join(sorted(FLOP_PER_CLK_PER_CU))})")
    return FLOP_PER_CLK_PER_CU[arch]


def cache_estimate(sizes_mib, rates, eligible=None,
                   min_ratio: float = MIN_CACHE_RATIO,
                   near: float = NEAR_PLATEAU):
    """Capacity of the last level cache the sweep can see, in MiB, or None.

    A memory-attached cache rolls off gradually rather than falling off a
    cliff -- at twice its capacity half the traffic still hits -- so looking
    for one large step between adjacent sizes misses it and is noisy besides.
    Compare the plateau against the asymptote instead, and report the largest
    working set still served near plateau rate.

    `eligible` optionally restricts which indices may be used, for excluding
    measurements too short to trust. Pure, so the sweep's interpretation is
    testable without a GPU.
    """
    idx = [i for i in range(len(rates))
           if eligible is None or i in eligible]
    if len(idx) < 2:
        return None
    floor = rates[idx[-1]]                    # asymptote: the largest size swept
    peak = max(rates[i] for i in idx)
    if floor <= 0 or peak / floor < min_ratio:
        return None
    cut = peak - near * (peak - floor)
    return max(sizes_mib[i] for i in idx if rates[i] >= cut)


def timed_us(fn, iters: int = 30) -> float:
    """Median-free mean microseconds per call, after a warm-up."""
    for _ in range(5):
        fn()
    torch.cuda.synchronize()
    s, e = torch.cuda.Event(True), torch.cuda.Event(True)
    s.record()
    for _ in range(iters):
        fn()
    e.record()
    torch.cuda.synchronize()
    return s.elapsed_time(e) / iters * 1e3


def tbs(moved_bytes: float, us: float) -> float:
    return moved_bytes / (us * 1e-6) / 1e12


def sustained_sclk_mhz(device: int = 0, seconds: float = 12.0,
                       warmup: float = 3.0) -> float:
    """Median engine clock while this process hammers the Matrix Cores.

    Matched to our own device by PCI BDF: these boxes are usually shared, and
    the maximum over all agents would happily report someone else's job.
    """
    import amdsmi

    props = torch.cuda.get_device_properties(device)
    want = (f"{props.pci_domain_id:04x}:{props.pci_bus_id:02x}:"
            f"{props.pci_device_id:02x}.0")

    amdsmi.amdsmi_init()
    try:
        handle = next(
            (h for h in amdsmi.amdsmi_get_processor_handles()
             if amdsmi.amdsmi_get_gpu_device_bdf(h).lower() == want), None)
        if handle is None:
            raise RuntimeError(f"no amdsmi handle matches this device ({want})")

        stop = threading.Event()

        def load():
            # A fresh thread starts on device 0 regardless of the caller's
            # current device, so without this the load lands on the wrong GPU
            # and we sample an idle clock for a part that is doing nothing.
            torch.cuda.set_device(device)
            a = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
            b = torch.randn(8192, 8192, device="cuda", dtype=torch.float16)
            while not stop.is_set():
                for _ in range(20):
                    a @ b
                torch.cuda.synchronize()

        t = threading.Thread(target=load, daemon=True)
        t.start()
        try:
            samples, elapsed, step = [], 0.0, 0.5
            while elapsed < seconds:
                stop.wait(step)
                elapsed += step
                if elapsed < warmup:      # let the governor ramp before sampling
                    continue
                samples.append(amdsmi.amdsmi_get_clock_info(
                    handle, amdsmi.AmdSmiClkType.SYS)["clk"])
        finally:
            stop.set()
            t.join(timeout=30)
        return statistics.median(samples)
    finally:
        amdsmi.amdsmi_shut_down()


def compute_roof(device: int, cu: int, fpc: int, seconds: float) -> None:
    try:
        sclk = sustained_sclk_mhz(device, seconds)
    except Exception as exc:                  # noqa: BLE001 -- report, never guess
        print(f"compute: SKIPPED -- could not sample the clock ({exc}).")
        print("         Without a measured clock there is no honest peak, and "
              "a boost figure would overstate it.")
        return

    peak = cu * fpc * sclk * 1e6
    print(f"compute: sustained sclk {sclk:.0f} MHz under dense MFMA load")
    print(f"         {cu} CU x {fpc} FLOP/clk x {sclk / 1000:.3f} GHz"
          f" = {peak / 1e12:.0f} TFLOP/s f16/bf16")

    # Cross-check the constant from the top of the stack. Nothing may exceed the
    # roofline, so over 100% means the table is wrong for this part.
    M = 8192
    a = torch.randn(M, M, device="cuda", dtype=torch.float16)
    b = torch.randn(M, M, device="cuda", dtype=torch.float16)
    got = 2.0 * M * M * M / (timed_us(lambda: torch.mm(a, b), 30) * 1e-6)
    pct = 100 * got / peak
    print(f"         torch.mm {M}^3 reaches {got / 1e12:.1f} TFLOP/s = {pct:.0f}%"
          f" of it ({got / (cu * sclk * 1e6):.0f} FLOP/clk/CU of {fpc})")
    if pct > 100:
        print("         *** over 100%: the FLOP/clk constant is too low for this "
              "part. Fix it before quoting any percentage. ***")
    del a, b
    torch.cuda.empty_cache()


def memory_roof(sizes_gib=(2, 8)) -> None:
    print("memory : streaming rate, working set far past any cache")
    for gib in sizes_gib:
        n = gib * 1024**3 // 2
        a = torch.randn(n, dtype=torch.float16, device="cuda")
        b = torch.empty_like(a)
        grid = (triton.cdiv(n, BLOCK),)
        acc = torch.empty(grid[0], dtype=torch.float32, device="cuda")
        r = tbs(n * 2, timed_us(lambda: _read[grid](a, n, acc, BLOCK)))
        c = tbs(2 * n * 2, timed_us(lambda: _copy[grid](a, b, n, BLOCK)))
        print(f"         {gib:>2} GiB   read {r:5.2f} TB/s   "
              f"copy (r+w) {c:5.2f} TB/s")
        del a, b, acc
        torch.cuda.empty_cache()


def cache_knee(device: int, sizes_mib=CACHE_SIZES_MIB) -> None:
    l2 = torch.cuda.get_device_properties(device).L2_cache_size / 2**20
    print(f"cache  : L2 reported as {l2:.0f} MiB. Sweeping a re-read working "
          f"set for further levels")

    rows = []
    for mib in sizes_mib:
        n = mib * 1024**2 // 2
        a = torch.randn(n, dtype=torch.float16, device="cuda")
        grid = (triton.cdiv(n, BLOCK),)
        acc = torch.empty(grid[0], dtype=torch.float32, device="cuda")
        us = timed_us(lambda: _read[grid](a, n, acc, BLOCK))
        rows.append((mib, us, tbs(n * 2, us)))
        del a, acc
        torch.cuda.empty_cache()

    rates = [r for _, _, r in rows]
    eligible = {i for i, (_, us, _) in enumerate(rows) if us >= MIN_US_FOR_KNEE}
    capacity = cache_estimate([m for m, _, _ in rows], rates, eligible)

    print(f"         {'size':>9} {'per call':>9} {'read':>9}")
    for mib, us, r in rows:
        note = ""
        if mib == capacity:
            note = "  <-- last size still at cache rate"
        elif us < MIN_US_FOR_KNEE:
            note = "  (too short to trust; launch cost understates it)"
        print(f"         {mib:>6} MiB {us:>8.1f}us {r:>6.2f} TB/s{note}")

    if capacity is None:
        print("\n         No cache found: every size here behaves like DRAM.")
    else:
        print(f"\n         Last level holds about {capacity} MiB "
              f"({max(rates):.2f} TB/s in cache vs {rates[-1]:.2f} DRAM). A "
              f"benchmark\n         whose working set fits in it is not "
              f"measuring DRAM -- check yours before\n         dividing by the "
              f"streaming roof.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--what", default="compute,memory,cache",
                   help="comma-separated: compute, memory, cache")
    p.add_argument("--flop-per-clk", type=int, default=None,
                   help="override the per-CU dense f16 FLOP/clk constant")
    p.add_argument("--clock-seconds", type=float, default=12.0,
                   help="how long to hold the MFMA load while sampling sclk")
    a = p.parse_args()

    torch.cuda.set_device(a.device)
    d = torch.cuda.get_device_properties(a.device)
    arch = arch_of(a.device)
    print(f"device : {d.name} ({arch})  {d.multi_processor_count} CU  "
          f"{d.total_memory / 2**30:.0f} GiB\n")

    what = [w.strip() for w in a.what.split(",") if w.strip()]
    if "compute" in what:
        compute_roof(a.device, d.multi_processor_count,
                     flop_per_clk(arch, a.flop_per_clk), a.clock_seconds)
        print()
    if "memory" in what:
        memory_roof()
        print()
    if "cache" in what:
        cache_knee(a.device)


if __name__ == "__main__":
    main()
