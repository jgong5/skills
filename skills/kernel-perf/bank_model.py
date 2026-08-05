#!/usr/bin/env python3
"""LDS bank-conflict model for CDNA.

LDS is 32 banks x 4 B and retires 128 B per cycle, so an access of W bytes per
lane is served 128/W consecutive lanes at a time. A group is conflict-free when
its dwords cover 32 distinct banks; if one bank owes n distinct dwords, the
group costs n cycles.

Use it to choose a layout before writing it:

    from bank_model import cycles, ideal
    # a 16x16x16 fragment read: lane l takes 4 halves at (l%16)*LDA + 4*(l/16)
    cycles(lambda l: ((l % 16) * LDA + 4 * (l // 16)) * 2, 8)

Run directly for a worked example over candidate row strides.
"""

BANKS = 32
BANK_BYTES = 4
LANES = 64


def cycles(addr_of_lane, bytes_per_lane, lanes=LANES, banks=BANKS,
           bank_bytes=BANK_BYTES):
    """Cycles one wave-wide LDS access costs.

    addr_of_lane(l) -> byte address for lane l. Returns cycles for the whole
    wave; compare against ideal() for the same access.
    """
    per_cycle = banks * bank_bytes // bytes_per_lane
    if per_cycle < 1:
        raise ValueError(f"{bytes_per_lane} B/lane exceeds one cycle's {banks * bank_bytes} B")
    worst = 0
    for group in range(0, lanes, per_cycle):
        owed = {}
        for lane in range(group, group + per_cycle):
            addr = addr_of_lane(lane)
            if addr % bytes_per_lane:
                raise ValueError(f"lane {lane} address {addr} unaligned for {bytes_per_lane} B")
            for d in range(bytes_per_lane // bank_bytes):
                dword = addr // bank_bytes + d
                owed.setdefault(dword % banks, set()).add(dword)
        worst = max(worst, max(len(v) for v in owed.values()))
    return worst * (lanes // per_cycle)


def ideal(bytes_per_lane, lanes=LANES, banks=BANKS, bank_bytes=BANK_BYTES):
    """Conflict-free cycle count for the same access."""
    return lanes * bytes_per_lane // (banks * bank_bytes)


def conflict_factor(addr_of_lane, bytes_per_lane, **kw):
    """1.0 means conflict-free; 8.0 means it costs eight times its floor."""
    return cycles(addr_of_lane, bytes_per_lane, **kw) / ideal(bytes_per_lane, **kw)


if __name__ == "__main__":
    # Worked example: a 16x16x16 A/B fragment read out of a row-major tile of
    # 16-bit elements, against candidate row strides (LDA, in elements).
    #
    # Reads take 4 elements per lane at (l%16)*LDA + 4*(l/16); the staging
    # store writes 8 elements per lane at (t/4)*LDA + (t%4)*8. The point of the
    # example is that the two disagree about which strides are good.
    def factor(fn, width):
        try:
            return f"{conflict_factor(fn, width):.0f}x"
        except ValueError:
            return "unaligned"     # a stride this wide store cannot even use

    print(f"{'LDA':>5} {'b64 read':>10} {'b128 store':>12}")
    for lda in (32, 36, 40, 48, 64, 72):
        read = factor(lambda l: ((l % 16) * lda + 4 * (l // 16)) * 2, 8)
        store = factor(lambda l: ((l // 4) * lda + (l % 4) * 8) * 2, 16)
        print(f"{lda:>5} {read:>10} {store:>12}")
    print("\nNo stride is conflict-free for both: the strides that fix the read")
    print("cannot carry a 16 B store at all. That is the situation forcing a")
    print("narrower store, a permuted store mapping, or a swizzled layout --")
    print("see modelling.md.")
