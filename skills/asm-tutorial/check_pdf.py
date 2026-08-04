#!/usr/bin/env python3
"""Verify a tutorial PDF against the markdown it was rendered from.

    <skill-dir>/check_pdf.py <doc.pdf> <doc.md>

Mechanical checks, over every page:
  * every font pdffonts reports is embedded
  * every code line in the markdown appears verbatim (mod whitespace) in the
    pdftotext -layout extraction -- a line that wrapped in the PDF comes back
    split across two lines and fails this
  * every "section N" / "sections N and M" cross-reference in the markdown
    resolves to a "## N." heading that exists
  * pdfinfo reports a page count

Then reports which page number carries each of six pages worth a visual
look: title, contents, the widest code block, a table, a dense prose page,
the last page. It only reports page numbers -- rasterizing them is a
separate, manual step (`pdftoppm -f N -l N -png <doc.pdf> page`).

Exit 0 means clean -- prints a one-line "clean: N pages..." summary plus the
sample-page table. Exit 1 means read the PROBLEM: lines on stderr.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^##\s+(\d+)\.\s")
XREF_RE = re.compile(r"\b[Ss]ections?\s+(\d+)(?:\s+and\s+(\d+))?")
TABLE_ROW_RE = re.compile(r"^\s*\|")


def code_lines(md_text: str) -> list[str]:
    """Non-blank lines inside fenced code blocks, in order."""
    out = []
    in_fence = False
    for ln in md_text.splitlines():
        if FENCE_RE.match(ln.strip()):
            in_fence = not in_fence
            continue
        if in_fence and ln.strip():
            out.append(ln)
    return out


def parse_pdffonts(text: str) -> list[str]:
    """Return the names of fonts pdffonts reports as NOT embedded."""
    lines = text.splitlines()
    header = next((ln for ln in lines if ln.strip().startswith("name")), None)
    if header is None:
        return []
    emb_col = header.index("emb")
    type_col = header.index("type")
    unembedded = []
    for ln in lines:
        if not ln or ln is header or set(ln.strip()) <= {"-", " "}:
            continue
        name = ln[:type_col].strip()
        if not name:
            continue
        emb = ln[emb_col:emb_col + 3].strip()
        if emb != "yes":
            unembedded.append(name)
    return unembedded


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def wrapped_lines(md_text: str, pdf_text: str) -> list[str]:
    """Markdown code lines that do not appear (mod whitespace) in the PDF
    extraction. `pdftotext -layout` reconstructs whitespace runs from glyph
    column positions, not the source's literal space count, so a
    right-aligned comment column (exactly what annotate_asm.py's COMMENT_COL
    padding produces) can come back with a different number of internal
    spaces even though every word survived intact and in order. Comparing on
    collapsed whitespace, not the raw string, is what "verbatim (mod
    whitespace)" in this module's docstring actually means -- comparing only
    on `.strip()`'d ends is stricter than that and flags lines that never
    wrapped at all.
    """
    haystack = {_normalize_ws(ln) for ln in pdf_text.splitlines()}
    return [ln for ln in code_lines(md_text)
            if ln.strip() and _normalize_ws(ln) not in haystack]


def broken_xrefs(md_text: str) -> list[str]:
    """"section N" references in the prose with no matching "## N." heading."""
    headings = {int(m.group(1)) for m in
                (HEADING_RE.match(ln) for ln in md_text.splitlines()) if m}
    broken = []
    in_fence = False
    for ln in md_text.splitlines():
        if FENCE_RE.match(ln.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in XREF_RE.finditer(ln):
            for g in m.groups():
                if g is not None and int(g) not in headings:
                    context = ln[m.start():m.start() + 70].strip()
                    broken.append(f"{m.group(0)!r} (no '## {g}.' heading): "
                                  f"{context}")
    return broken


def pages(pdf_text: str) -> list[str]:
    """Split `pdftotext -layout`'s output into per-page text."""
    parts = pdf_text.split("\f")
    return parts[:-1] if parts and parts[-1] == "" else parts


def _table_header_cells(md_text: str) -> list[str] | None:
    """The header row's cell texts for the first markdown table found
    outside a fenced code block, e.g. ["Constant", "Value", "Source"].
    Pandoc renders a GFM table as an HTML <table>; no pipe character
    survives into `pdftotext`'s output, so hunting the rendered page text for
    markdown table syntax can never find anything -- the header cells' own
    words, rendered plainly, are the reliable anchor. Requiring every cell's
    text to be present, not just one, keeps a single short/common header
    word (e.g. "Value") from matching unrelated prose on the wrong page.
    """
    in_fence = False
    for ln in md_text.splitlines():
        if FENCE_RE.match(ln.strip()):
            in_fence = not in_fence
            continue
        if in_fence or not TABLE_ROW_RE.match(ln):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells if c):
            continue  # the GFM header/body separator row ("| --- | --- |")
        cells = [c for c in cells if c]
        if cells:
            return cells
    return None


def sample_pages(md_text: str, page_texts: list[str]) -> dict[str, int]:
    """1-indexed page numbers worth a visual look."""
    n = len(page_texts)
    result = {"title": 1, "last": n}
    for i, text in enumerate(page_texts, start=1):
        if "Contents" in text.splitlines()[:3]:
            result.setdefault("contents", i)
            break
    widest = max(code_lines(md_text), key=len, default=None)
    if widest:
        # Compare on collapsed whitespace, exactly like wrapped_lines: the
        # widest code line is the one annotate_asm.py's COMMENT_COL padding
        # makes most likely to have its internal spacing repadded by
        # pdftotext's column-position heuristic, so a raw substring check
        # here is the one place this bug bites hardest.
        target = _normalize_ws(widest)
        for i, text in enumerate(page_texts, start=1):
            if any(_normalize_ws(ln) == target for ln in text.splitlines()):
                result["widest_code"] = i
                break
    header_cells = _table_header_cells(md_text)
    if header_cells:
        for i, text in enumerate(page_texts, start=1):
            if all(c in text for c in header_cells):
                result["table"] = i
                break
    prose_candidates = [(i, len(text.split())) for i, text in enumerate(page_texts, start=1)
                        if i not in (result.get("title"), result.get("contents"))]
    if prose_candidates:
        result["prose"] = max(prose_candidates, key=lambda kv: kv[1])[0]
    return result


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_pdf.py <doc.pdf> <doc.md>", file=sys.stderr)
        return 1
    pdf, md = Path(argv[0]), Path(argv[1])
    md_text = md.read_text()
    pdf_text = run(["pdftotext", "-layout", str(pdf), "-"])
    fonts_text = run(["pdffonts", str(pdf)])
    info_text = run(["pdfinfo", str(pdf)])

    problems = []
    unembedded = parse_pdffonts(fonts_text)
    if unembedded:
        problems.append(f"unembedded fonts: {', '.join(unembedded)}")
    wrapped = wrapped_lines(md_text, pdf_text)
    if wrapped:
        problems.append(f"{len(wrapped)} code line(s) did not survive extraction "
                        "verbatim (likely wrapped): "
                        + "; ".join(repr(w) for w in wrapped[:5]))
    broken = broken_xrefs(md_text)
    if broken:
        problems.append(f"{len(broken)} broken cross-reference(s): "
                        + "; ".join(broken[:5]))
    page_count_m = re.search(r"^Pages:\s*(\d+)", info_text, re.MULTILINE)
    if not page_count_m:
        problems.append("pdfinfo did not report a page count")

    if problems:
        for p in problems:
            print(f"PROBLEM: {p}", file=sys.stderr)
        return 1

    page_texts = pages(pdf_text)
    samples = sample_pages(md_text, page_texts)
    print(f"clean: {len(page_texts)} pages, all fonts embedded")
    print("sample pages for a visual look:")
    for name in ("title", "contents", "widest_code", "table", "prose", "last"):
        if name in samples:
            print(f"  {name:<12} page {samples[name]}")
        else:
            print(f"  {name:<12} (none found)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
