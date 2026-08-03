"""Annotate the GCN assembly that build.sh emits, so it can be read.

`build.sh` drops raw `.s` files in `asm/`. They are correct and completely
opaque: 6000 lines of `v_lshl_add_u32` and `s_waitcnt lgkmcnt(6)` with no
indication of which parts are the GEMM and which are address arithmetic. This
reads those files and writes commented copies to `asm/annotated/`, adding

  * a per-file header: which kernels the file defines, the compiler's own
    register/LDS/occupancy report for each, and the instruction mix,
  * an end-of-line comment on every instruction it recognises,
  * decoded operands where the operands are the interesting part -- MFMA tile
    shapes, `s_waitcnt` counter semantics, LDS access widths,
  * banners at kernel entry and at loop headers.

Nothing here is guessed. Every claim is either a fixed property of the
target's CDNA ISA (see the ARCH table below and cdna-facts.md) or comes from
the compiler itself, via a `.resources` sidecar next to the input .s.
Occupancy in particular is the compiler's number and not a model of one: it
is the minimum over several independent limiters -- e.g. rocWMMA's 2
waves/SIMD is set by its 32 KB of LDS, not by the registers a reader would be
tempted to divide.

    ./shell.sh python3 /workspace/skills/skills/asm-tutorial/annotate_asm.py <in.s> [--out-dir DIR]

An arch not in the ARCH table below still gets instruction comments; it loses
MFMA cost and occupancy commentary, and a warning names it on stderr.

Only comments are added, so the output is still assembly. Checked with

    /opt/rocm/llvm/bin/clang -x assembler -target amdgcn-amd-amdhsa \\
        -mcpu=<arch> -c <out.s> -o /dev/null
"""

from __future__ import annotations

import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------
# gfx942 (CDNA3) facts used below. Kept here rather than inline so the numbers
# have one home and can be checked against the ISA guide in one place.
# --------------------------------------------------------------------------

TARGET_RE = re.compile(r'\.amdgcn_target\s+"amdgcn-amd-amdhsa--(\w+)"')

# CDNA facts, keyed by the target string on line 1 of every listing. One
# authoritative copy so the script cannot drift from a second one;
# cdna-facts.md documents each entry in prose with the guide it came from,
# for the reader rather than the parser. An arch missing here takes the
# unknown-target path: instruction comments only, no MFMA cost, no occupancy.
ARCH: dict[str, dict[str, object]] = {
    # FLOP/clk per Matrix Core, from the 2048 FLOP/clk/CU figure the
    # benchmark's compute roofline uses, divided by 4 Matrix Cores per CU.
    # Every MFMA in the rocWMMA listing is consistent with it:
    # cycles = 2*M*N*K / 512. That agreement is the reason to trust the
    # constant -- see the compute-peak note in the README and cdna-facts.md.
    "gfx942": {"name": "CDNA3", "wave": 64, "flop_per_clk_per_matrix_core": 512},
}


def detect_arch(lines: list[str]) -> str | None:
    """The `.amdgcn_target` string from the top of the listing, if present."""
    for ln in lines[:5]:
        m = TARGET_RE.search(ln)
        if m:
            return m.group(1)
    return None


def mfma_note(mnemonic: str, operands: str, arch: str) -> str:
    """Decode a v_mfma_* into tile shape, per-lane operand sizes and cost."""
    m = re.match(r"v_mfma_f32_(\d+)x(\d+)x(\d+)_?(f16|bf16|f32|bf16_1k)", mnemonic)
    if not m:
        return "matrix-core multiply-accumulate"
    tm, tn, tk, ty = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    facts = ARCH.get(arch)
    dst = operands.split(",")[0].strip() if operands else "?"
    if facts is None:
        return f"D[{tm}x{tn}] += A[{tm}x{tk}] * B[{tk}x{tn}] in {ty} -> {dst}"
    wave = facts["wave"]
    flop = 2 * tm * tn * tk
    cycles = flop // facts["flop_per_clk_per_matrix_core"]
    # One instruction computes a full tm x tn tile of C for the whole wave, so
    # each lane holds tm*tn/wave fp32 accumulators and tk*tm/wave A elements.
    acc_per_lane = tm * tn // wave
    a_per_lane = tm * tk // wave
    return (f"D[{tm}x{tn}] += A[{tm}x{tk}] * B[{tk}x{tn}] in {ty}, one per wave: "
            f"{acc_per_lane} fp32 acc + {a_per_lane}+{a_per_lane} {ty} per lane, "
            f"{flop} FLOP in ~{cycles} cyc -> {dst}")


def waitcnt_note(operands: str) -> str:
    """s_waitcnt names a *ceiling*, not a count to wait for."""
    parts = []
    for kind, n in re.findall(r"(vmcnt|lgkmcnt|expcnt)\((\d+)\)", operands):
        what = {
            "vmcnt": "vector memory (buffer/global/flat) ops",
            "lgkmcnt": "LDS, GDS, constant and message ops",
            "expcnt": "export/GDS writes",
        }[kind]
        if n == "0":
            parts.append(f"block until ALL outstanding {what} have returned")
        else:
            parts.append(f"block until at most {n} {what} are still in flight "
                         f"(lets the {n} most recent stay outstanding)")
    return "; ".join(parts) or "wait on memory counters"


# --------------------------------------------------------------------------
# Instruction glossary, keyed by mnemonic with the encoding suffix stripped.
# --------------------------------------------------------------------------

GLOSSARY: dict[str, str] = {
    # --- scalar memory -----------------------------------------------------
    "s_load_dword": "scalar load 4B from constant/kernarg memory -> SGPR",
    "s_load_dwordx2": "scalar load 8B (a 64-bit pointer) -> SGPR pair",
    "s_load_dwordx4": "scalar load 16B -> 4 SGPRs",
    "s_load_dwordx8": "scalar load 32B -> 8 SGPRs",
    # --- scalar ALU: one result for the whole wave, free of the VALU --------
    "s_mov_b32": "scalar move",
    "s_mov_b64": "scalar move, 64-bit pair",
    "s_movk_i32": "scalar move of a sign-extended 16-bit literal",
    "s_add_i32": "scalar integer add",
    "s_add_u32": "scalar add, low half (pairs with s_addc_u32)",
    "s_addc_u32": "scalar add with carry-in from SCC, high half",
    "s_sub_i32": "scalar integer subtract",
    "s_mul_i32": "scalar multiply, low 32 bits",
    "s_mul_hi_u32": "scalar multiply, high 32 bits",
    "s_max_i32": "scalar signed max",
    "s_abs_i32": "scalar absolute value",
    "s_and_b32": "scalar bitwise AND",
    "s_and_b64": "scalar AND on a 64-bit lane mask",
    "s_or_b64": "scalar OR on a 64-bit lane mask",
    "s_xor_b32": "scalar XOR",
    "s_xor_b64": "scalar XOR on a 64-bit lane mask",
    "s_andn2_b64": "lane mask AND NOT: dst = a & ~b",
    "s_lshl_b32": "scalar shift left",
    "s_lshl_b64": "scalar shift left, 64-bit",
    "s_lshr_b32": "scalar shift right, logical",
    "s_ashr_i32": "scalar shift right, arithmetic (sign-extending)",
    "s_cselect_b32": "scalar select on SCC",
    "s_cselect_b64": "scalar select on SCC, 64-bit",
    "s_bitcmp1_b32": "test one bit, result to SCC",
    "s_cmp_eq_u32": "scalar compare -> SCC",
    "s_cmp_lg_u32": "scalar compare not-equal -> SCC",
    "s_cmp_lt_i32": "scalar compare -> SCC",
    "s_cmp_lt_u32": "scalar compare -> SCC",
    "s_cmp_ge_i32": "scalar compare -> SCC",
    "s_cmp_ge_u32": "scalar compare -> SCC",
    "s_cmp_gt_i32": "scalar compare -> SCC",
    "s_cmpk_lt_u32": "scalar compare against a 16-bit literal -> SCC",
    # --- control flow ------------------------------------------------------
    "s_branch": "unconditional branch",
    "s_cbranch_scc0": "branch if SCC == 0",
    "s_cbranch_scc1": "branch if SCC == 1",
    "s_cbranch_vccnz": "branch if any lane set VCC",
    "s_cbranch_execz": "branch if EXEC is all-zero -- every lane took the "
                       "other side, so skip this block entirely",
    "s_cbranch_execnz": "branch if any lane is still active",
    "s_and_saveexec_b64": "enter a divergent region: save EXEC to dst, then "
                          "EXEC &= mask so only the taking lanes run",
    "s_andn2_saveexec_b64": "the else-side: save EXEC, then activate exactly "
                            "the lanes the if-side masked off",
    "s_endpgm": "end of wavefront",
    "s_barrier": "workgroup barrier -- all waves in the group must arrive "
                 "before any proceeds; this is what makes LDS handoff safe",
    "s_icache_inv": "invalidate the instruction cache",
    "s_nop": "wait states. Not padding: some sequences (notably writing an "
             "AGPR then having an MFMA read it) have a hardware hazard the "
             "compiler must cover with a fixed number of idle cycles",
    # --- vector ALU: one result per lane -----------------------------------
    "v_mov_b32": "per-lane move",
    "v_add_u32": "per-lane add",
    "v_sub_u32": "per-lane subtract",
    "v_add_co_u32": "per-lane add, carry-out to a lane mask",
    "v_add3_u32": "per-lane 3-way add, one instruction",
    "v_mul_lo_u32": "per-lane 32x32 multiply, low half",
    "v_mad_u64_u32": "per-lane 32x32+64 multiply-add, unsigned",
    "v_mad_i64_i32": "per-lane 32x32+64 multiply-add, signed -- typically a "
                     "row/col index scaled to a byte offset",
    "v_lshlrev_b32": "per-lane shift left (operands reversed: shift is src0)",
    "v_lshrrev_b32": "per-lane shift right (operands reversed)",
    "v_ashrrev_i32": "per-lane arithmetic shift right (operands reversed)",
    "v_lshl_add_u32": "fused (a << b) + c",
    "v_lshl_add_u64": "fused (a << b) + c, 64-bit -- pointer arithmetic",
    "v_add_lshl_u32": "fused (a + b) << c",
    "v_lshl_or_b32": "fused (a << b) | c -- packing index bits",
    "v_and_or_b32": "fused (a & b) | c -- packing index bits",
    "v_or3_b32": "3-way OR, one instruction",
    "v_and_b32": "per-lane AND",
    "v_or_b32": "per-lane OR",
    "v_xor_b32": "per-lane XOR",
    "v_bfe_u32": "bitfield extract (src, offset, width). At kernel entry v0 "
                 "packs the workitem id as x[9:0] y[19:10] z[29:20], so this "
                 "is how threadIdx.y/.z are unpacked",
    "v_bfrev_b32": "bit reverse",
    "v_cndmask_b32": "per-lane select from a 64-bit lane mask -- a branchless if",
    "v_readfirstlane_b32": "broadcast the first active lane's value to an SGPR",
    "v_cvt_f16_f32": "convert fp32 -> fp16, round to nearest even",
    "v_cvt_f32_u32": "convert u32 -> fp32",
    "v_cvt_u32_f32": "convert fp32 -> u32",
    "v_rcp_iflag_f32": "fp32 reciprocal approximation -- part of the "
                       "integer-divide expansion, since there is no integer "
                       "divide instruction",
    "v_fmac_f32": "per-lane fp32 fused multiply-accumulate, dst += a*b",
    "v_fma_mix_f32": "fp32 FMA reading 16-bit source halves selected by "
                     "op_sel. This is the scalar fallback for fp16 math: one "
                     "MAC per instruction, against 512 FLOP/clk for an MFMA",
    # --- accumulation registers -------------------------------------------
    "v_accvgpr_write_b32": "arch VGPR -> accumulation VGPR (AGPR). MFMA "
                           "accumulators live in the AGPR file",
    "v_accvgpr_read_b32": "AGPR -> arch VGPR, so the result can be converted "
                          "and stored",
    # --- LDS ---------------------------------------------------------------
    "ds_read_u16": "LDS read, 2B zero-extended",
    "ds_read_b128": "LDS read, 16B per lane -- the widest LDS access, one "
                    "instruction feeding a whole MFMA operand",
    "ds_read2_b64": "two independent 8B LDS reads in one instruction; "
                    "offset0/offset1 are in units of 8B",
    "ds_write_b16": "LDS write, 2B",
    "ds_write_b16_d16_hi": "LDS write of the *high* 16 bits of the source -- "
                           "unpacking two halves from one VGPR without a shift",
    "ds_write_b128": "LDS write, 16B per lane",
    # --- global / buffer memory -------------------------------------------
    "global_load_ushort": "global load 2B, flat address in a VGPR pair",
    "global_load_dwordx4": "global load 16B",
    "global_store_short": "global store 2B",
    "buffer_load_dwordx4": "buffer load 16B through an SRD (base + stride + "
                           "num_records in 4 SGPRs). The hardware range-checks "
                           "against num_records: out-of-range reads return 0 "
                           "and writes are dropped, which is why a correct SRD "
                           "removes the need for bounds predication",
    "buffer_store_dwordx4": "buffer store 16B through an SRD, range-checked",
    "buffer_atomic_pk_add_f16": "atomic add of two packed fp16 to memory. "
                                "This is a split-K epilogue: partial tiles "
                                "from several workgroups are summed in place "
                                "rather than in a second pass",
    "global_atomic_pk_add_bf16": "atomic add of two packed bf16 to memory -- "
                                 "the bf16 split-K epilogue",
}

# Families, tried when the exact mnemonic is not in GLOSSARY.
PREFIX_RULES: list[tuple[str, str]] = [
    ("v_mfma_", "matrix-core multiply-accumulate"),
    ("v_cmp_", "per-lane compare; the result is a 64-bit mask, one bit per lane"),
    ("s_cmp_", "scalar compare -> SCC"),
    ("s_cbranch_", "conditional branch"),
    ("ds_read", "LDS read"),
    ("ds_write", "LDS write"),
    ("buffer_", "buffer memory op through an SRD"),
    ("global_", "global memory op"),
    ("s_", "scalar op"),
    ("v_", "per-lane vector op"),
]

# Encoding suffixes carry no semantics worth a comment of their own.
SUFFIX_RE = re.compile(r"_(e32|e64|sdwa|dpp)$")

SUFFIX_NOTE = {
    "e64": "VOP3 encoding (extra operands/modifiers)",
    "sdwa": "sub-dword addressing: operates on a byte/word field in place",
    "dpp": "cross-lane data-parallel primitive",
}


def describe(mnemonic: str, operands: str, arch: str | None) -> tuple[str, str]:
    """Return (comment, base mnemonic) for one instruction."""
    base = SUFFIX_RE.sub("", mnemonic)
    suffix_m = SUFFIX_RE.search(mnemonic)

    if base.startswith("v_mfma_"):
        note = mfma_note(base, operands, arch) if arch else "matrix-core multiply-accumulate"
    elif base == "s_waitcnt":
        note = waitcnt_note(operands)
    elif base in GLOSSARY:
        note = GLOSSARY[base]
    else:
        note = next((d for p, d in PREFIX_RULES if base.startswith(p)), "")

    if suffix_m and suffix_m.group(1) in SUFFIX_NOTE and note:
        note = f"{note}  [{SUFFIX_NOTE[suffix_m.group(1)]}]"
    return note, base


# --------------------------------------------------------------------------
# File-level analysis
# --------------------------------------------------------------------------

INSTR_RE = re.compile(r"^(\s+)([a-z][a-z0-9_]*)(\s*)(.*?)\s*$")
DIRECTIVE_RE = re.compile(r"^\s*\.")
LABEL_RE = re.compile(r"^([.\w$]+):")
FUNC_TYPE_RE = re.compile(r"^\s*\.type\s+([^,]+),\s*@function")

CATEGORIES = [
    ("matrix core (MFMA)", lambda b: b.startswith("v_mfma")),
    ("accumulator moves", lambda b: b.startswith("v_accvgpr")),
    ("LDS", lambda b: b.startswith("ds_")),
    ("global/buffer memory", lambda b: b.startswith(("global_", "buffer_"))),
    ("scalar memory", lambda b: b.startswith("s_load")),
    ("synchronisation", lambda b: b in ("s_waitcnt", "s_barrier", "s_nop")),
    ("control flow", lambda b: b.startswith(("s_branch", "s_cbranch", "s_cmp"))
                               or "saveexec" in b or b == "s_endpgm"),
    ("vector ALU (addressing, convert)", lambda b: b.startswith("v_")),
    ("scalar ALU", lambda b: b.startswith("s_")),
]


def categorise(base: str) -> str:
    for name, test in CATEGORIES:
        if test(base):
            return name
    return "other"


def read_resources(path: Path) -> list[dict[str, str]]:
    """Parse the `.resources` sidecar build.sh captures from the compiler.

    These are the compiler's own numbers, not ours. That matters most for
    occupancy: it is the minimum over several independent limiters (registers,
    LDS, workgroup size), so it cannot be derived from the register counts
    alone, and reimplementing the model here would only produce a number that
    disagrees with the compiler for reasons a reader could not see.
    """
    side = path.with_suffix(".resources")
    if not side.exists():
        return []
    out, cur = [], None
    for ln in side.read_text().splitlines():
        key, _, val = ln.strip().partition(":")
        key, val = key.strip(), val.strip()
        if key == "Function Name":
            cur = {"name": val}
            out.append(cur)
        elif cur is not None and key:
            cur[key] = val
    return out


RESOURCE_GLOSS = {
    "TotalSGPRs": "scalar registers",
    "VGPRs": "arch vector registers per lane",
    "AGPRs": "accumulation registers per lane (MFMA operands live here)",
    "ScratchSize [bytes/lane]": "private/scratch spill area; 0 is what you want",
    "Occupancy [waves/SIMD]": "concurrent waves per SIMD, min over all limiters",
    "SGPRs Spill": "scalar spills; nonzero means the kernel ran out of SGPRs",
    "VGPRs Spill": "vector spills; nonzero costs memory traffic in the hot loop",
    "LDS Size [bytes/block]": "LDS per workgroup, out of 64 KiB per CU",
}

RESOURCE_ORDER = ["VGPRs", "AGPRs", "TotalSGPRs", "LDS Size [bytes/block]",
                  "Occupancy [waves/SIMD]", "VGPRs Spill", "SGPRs Spill",
                  "ScratchSize [bytes/lane]"]

LEN_PREFIX_RE = re.compile(r"\d+")


def short_name(mangled: str) -> str:
    """Pull the readable part out of an Itanium-mangled symbol.

    Not a demangler. It walks the leading length-prefixed components and
    stops at the template arguments, which is the part worth reading --
    `ck::kernel_gemm_xdl_cshuffle_v3` -- and none of the 500 characters of
    tile constants that follow it. Anything it cannot parse comes back
    unchanged.
    """
    if not mangled.startswith("_Z"):
        return mangled
    rest = mangled[2:]
    if rest.startswith("N"):
        rest = rest[1:]
    parts = []
    while rest:
        if rest[0] == "L":            # internal-linkage marker
            rest = rest[1:]
            continue
        m = LEN_PREFIX_RE.match(rest)
        if not m:
            break
        n = int(m.group(0))
        rest = rest[m.end():]
        parts.append(rest[:n])
        rest = rest[n:]
    if not parts:
        return mangled
    return "::".join("(anon)" if p.startswith("_GLOBAL__N_") else p
                     for p in parts)


def discriminators(names: list[str]) -> list[str]:
    """For symbols that shorten to the same thing, say where they differ.

    CK instantiates the same kernel template four times here, and the
    difference is one character 282 into the mangled name and another 271
    characters after that. Printing four 595-character names would bury it;
    printing four identical short names would hide it. So print the short
    name and, beside it, only the substrings that actually vary.
    """
    if len(names) < 2:
        return [""] * len(names)
    if len({len(n) for n in names}) != 1:
        # Unequal lengths: fall back to the span between the common prefix
        # and the common suffix, which is coarser but always correct.
        pre = len(_common_affix(names))
        suf = len(_common_affix([n[::-1] for n in names]))
        return [f"...{n[pre:len(n) - suf][:56]}..." for n in names]
    n = len(names[0])
    varying = [i for i in range(n) if len({s[i] for s in names}) > 1]
    runs: list[list[int]] = []
    for i in varying:
        if runs and i - runs[-1][1] <= 12:   # merge near-adjacent differences
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    return [" ".join(f"...{s[max(0, a - 12):a]}[{s[a:b]}]" for a, b in runs)
            for s in names]


def body_sizes(lines: list[str]) -> dict[str, int]:
    """Instructions in each top-level function body, by symbol name.

    Used only to spot the empty ones. CK's four kernel instantiations here
    are not four kernels: two of them are a bare `s_endpgm`, and saying so
    beside their all-zero register counts saves a reader hunting for a body
    that is not there.
    """
    sizes: dict[str, int] = {}
    cur = None
    for ln in lines:
        lm = LABEL_RE.match(ln)
        if lm and not ln.startswith((" ", "\t")):
            cur = None if lm.group(1).startswith(".L") else lm.group(1)
            if cur:
                sizes[cur] = 0
            continue
        if cur is None or DIRECTIVE_RE.match(ln) or ln.lstrip().startswith(";"):
            continue
        if INSTR_RE.match(ln):
            sizes[cur] += 1
    return sizes


def _common_affix(strings: list[str]) -> str:
    first = strings[0]
    for i, ch in enumerate(first):
        if any(len(s) <= i or s[i] != ch for s in strings):
            return first[:i]
    return first


def header(path: Path, lines: list[str], mix: Counter, bases: Counter,
           arch: str | None) -> list[str]:
    descs = read_resources(path)
    sizes = body_sizes(lines)
    facts = ARCH.get(arch) if arch else None
    if facts:
        arch_line = f"; {path.name} -- annotated GCN assembly for {arch} ({facts['name']})"
    elif arch:
        arch_line = f"; {path.name} -- annotated GCN assembly for {arch} (unrecognized target)"
    else:
        arch_line = f"; {path.name} -- annotated GCN assembly (no .amdgcn_target found)"
    out = [
        "; " + "=" * 76,
        arch_line,
        "; " + "=" * 76,
        ";",
        "; Generated by the amd-gpu:asm-tutorial skill's annotate_asm.py from a raw .s.",
        "; Comments are added mechanically; the instructions are untouched, so",
        "; this file still assembles. Regenerate with:",
        ";     ./shell.sh python3 /workspace/skills/skills/asm-tutorial/annotate_asm.py <in.s>",
        ";",
        "; Register files, and why the assembly keeps moving between them:",
        ";   s0, s[0:1]   SGPR. One value for the whole 64-lane wave. Used for",
        ";                anything uniform: kernel arguments, loop counters,",
        ";                base pointers, lane masks.",
        ";   v0, v[0:1]   VGPR. One value per lane.",
        ";   a0, a[0:3]   AGPR, the accumulation file. MFMA reads and writes",
        ";                its accumulator here, so results must be copied out",
        ";                with v_accvgpr_read before they can be stored.",
        ";   EXEC         64-bit lane mask. A 'branch' inside a wave is usually",
        ";                not a branch at all -- it masks lanes off via EXEC and",
        ";                runs both sides.",
        ";   SCC          scalar condition code, set by s_cmp_* and friends.",
        ";   vcc          the default 64-bit mask destination for v_cmp_*.",
        ";",
        "; Memory ordering is explicit. Loads are issued asynchronously and",
        "; counted; s_waitcnt is the only thing that makes a result visible.",
        "; vmcnt counts vector memory, lgkmcnt counts LDS and scalar memory.",
        ";",
    ]

    if descs:
        out += ["; Kernel resource usage, as reported by the compiler",
                "; (-Rpass-analysis=kernel-resource-usage, captured by build.sh).",
                "; Names are shortened; the full mangled symbol is on the label",
                "; at the top of each kernel body."]
        shorts = [short_name(d["name"]) for d in descs]
        # Several instantiations of one template shorten to the same name, so
        # work out what distinguishes them before printing any of them.
        groups: dict[str, list[int]] = {}
        for i, s in enumerate(shorts):
            groups.setdefault(s, []).append(i)
        marks: list[tuple[str, str] | None] = [None] * len(descs)
        for idxs in groups.values():
            if len(idxs) < 2:
                continue
            tags = discriminators([descs[i]["name"] for i in idxs])
            for k, (i, tag) in enumerate(zip(idxs, tags)):
                marks[i] = (f"[{k + 1} of {len(idxs)}]", tag)
        for d, s, mark in zip(descs, shorts, marks):
            out.append(";")
            out.append(f";   {s}" + (f"   {mark[0]}" if mark else ""))
            if mark and mark[1]:
                wrapped = textwrap.wrap(mark[1], 60)
                out.append(f";     differs at  {wrapped[0]}")
                out += [f";                  {c}" for c in wrapped[1:]]
            for key in RESOURCE_ORDER:
                if key not in d:
                    continue
                gloss = RESOURCE_GLOSS.get(key, "")
                out.append(f";     {key:<24} {d[key]:>8}   {gloss}")
            if sizes.get(d["name"], 99) <= 2:
                out += [
                    ";     ^ the body is one s_endpgm and nothing else: for these",
                    ";       template parameters the kernel folded away, and the",
                    ";       symbol is all that is left of it.",
                ]
        out.append(";")
    elif any("amdhsa_kernel" in ln for ln in lines):
        out += ["; (No .resources sidecar next to the source .s -- rebuild with",
                ";  build.sh to get the compiler's register/occupancy report.)",
                ";"]
    else:
        out += [
            "; No kernel in this file: this translation unit contains no device",
            "; code of its own. For hipBLASLt that is expected -- it calls into",
            "; the library, whose kernels live in its own code objects and never",
            "; pass through this compile.",
            ";",
        ]

    total = sum(mix.values())
    if total:
        out.append(f"; Instruction mix ({total} instructions):")
        for name, n in mix.most_common():
            out.append(f";   {name:<34} {n:>6}  {100 * n / total:>5.1f}%")
        out.append(";")
        mfmas = {b: c for b, c in bases.items() if b.startswith("v_mfma")}
        if mfmas:
            out.append("; Matrix instructions selected:")
            for b, c in sorted(mfmas.items(), key=lambda kv: -kv[1]):
                out.append(f";   {b} x{c}")
            out.append(";")
    out.append("; " + "=" * 76)
    out.append("")
    return out


BANNER_LOOP = "loop body begins here"
COMMENT_COL = 60


def annotate(path: Path, out_dir: Path) -> tuple[Path, int]:
    lines = path.read_text().splitlines()
    arch = detect_arch(lines)
    if arch is not None and arch not in ARCH:
        print(f"warning: {path.name}: unrecognized target {arch!r} -- "
              f"instruction comments only, no MFMA cost or occupancy",
              file=sys.stderr)

    # Only label functions as functions. The assembler also emits top-level
    # labels for data -- `__hip_cuid_...` is a one-byte object in .bss -- and
    # banner-ing those as a kernel body is how the hipblaslt file, which has
    # no device code at all, ended up looking like it had a kernel in it.
    funcs = {m.group(1) for m in
             (FUNC_TYPE_RE.match(ln) for ln in lines) if m}

    mix: Counter = Counter()
    bases: Counter = Counter()
    for ln in lines:
        if DIRECTIVE_RE.match(ln) or not ln.strip() or ln.lstrip().startswith(";"):
            continue
        m = INSTR_RE.match(ln)
        if m:
            base = SUFFIX_RE.sub("", m.group(2))
            bases[base] += 1
            mix[categorise(base)] += 1

    out = header(path, lines, mix, bases, arch)
    prev_note = None
    annotated = 0
    in_metadata = False

    for ln in lines:
        stripped = ln.strip()

        # The YAML metadata block is its own language; pass it through, but say
        # what it is the first time.
        if stripped.startswith(".amdgpu_metadata"):
            in_metadata = True
            out += ["", "; ---- runtime metadata: how the HSA loader sets the kernel up.",
                    "; ---- .args lists the kernarg layout, including the hidden",
                    "; ---- arguments HIP appends (block counts, group sizes).", ""]
            out.append(ln)
            continue
        if stripped.startswith(".end_amdgpu_metadata"):
            in_metadata = False
            out.append(ln)
            continue
        if in_metadata:
            out.append(ln)
            continue

        if stripped.startswith(".amdhsa_kernel"):
            name = stripped.split(None, 1)[1] if " " in stripped else "?"
            out += ["", "; " + "-" * 74,
                    f"; kernel descriptor for {name[:50]}",
                    "; the ABI contract: register budget, LDS size, which system",
                    "; values the hardware preloads into SGPRs/VGPRs before entry.",
                    "; " + "-" * 74]
            out.append(ln)
            prev_note = None
            continue

        # Function label: start of a kernel body.
        lm = LABEL_RE.match(ln)
        if lm and not ln.startswith((" ", "\t")) and lm.group(1) in funcs:
            out += ["", "; " + "=" * 74,
                    f"; KERNEL BODY: {short_name(lm.group(1))[:60]}",
                    "; on entry: s[0:1] = kernarg base pointer, s2/s3 = workgroup id",
                    ";           x/y, v0 = packed workitem id (see v_bfe_u32 below)",
                    "; " + "=" * 74]
            out.append(ln)
            prev_note = None
            continue

        # The compiler's own block comments make good anchors for loop banners.
        if stripped.startswith(";") and "Inner Loop Header" in stripped:
            out += ["", f"; >>>> {BANNER_LOOP} -- everything to the next backward",
                    ";      branch runs once per iteration.", ]
            out.append(ln)
            prev_note = None
            continue

        m = INSTR_RE.match(ln)
        if not m or DIRECTIVE_RE.match(ln) or stripped.startswith(";"):
            out.append(ln)
            if not stripped:
                prev_note = None
            continue

        indent, mnemonic, gap, operands = m.groups()
        note, _base = describe(mnemonic, operands, arch)
        if not note or note == prev_note:
            # Suppress a repeat of the identical comment: a run of 16 identical
            # MFMAs is easier to read with one explanation than sixteen.
            out.append(ln)
            prev_note = note or prev_note
            continue

        code = f"{indent}{mnemonic}{gap}{operands}".rstrip()
        pad = " " * max(1, COMMENT_COL - len(code.expandtabs(8)))
        out.append(f"{code}{pad}; {note}")
        prev_note = note
        annotated += 1

    dest = out_dir / path.name
    dest.write_text("\n".join(out) + "\n")
    return dest, annotated


def main(argv: list[str]) -> int:
    out_dir_flag = None
    targets = []
    it = iter(argv[1:])
    for a in it:
        if a == "--out-dir":
            out_dir_flag = Path(next(it))
        else:
            targets.append(Path(a))
    if not targets:
        print("usage: annotate_asm.py <in.s> [<in.s> ...] [--out-dir DIR]",
              file=sys.stderr)
        return 1

    for src in targets:
        if not src.exists():
            print(f"missing: {src}", file=sys.stderr)
            return 1
        out_dir = out_dir_flag or (src.resolve().parent / "annotated")
        out_dir.mkdir(parents=True, exist_ok=True)
        dest, n = annotate(src, out_dir)
        print(f"    {src.name:<26} -> {dest}  "
              f"({n} comments, {len(dest.read_text().splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
