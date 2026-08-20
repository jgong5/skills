#!/usr/bin/env python3
"""Verify an implementation study PDF against the markdown it was rendered from.

    <skill-dir>/check_pdf.py <doc.pdf> <doc.md>

Mechanical checks, over every page:
  * every font pdffonts reports is embedded
  * every code line in the markdown appears verbatim (mod whitespace) in the
    pdftotext -layout extraction -- a line that wrapped in the PDF comes back
    split across two lines and fails this
  * every "section N" / "sections N and M" cross-reference in the markdown
    resolves to a "## N." heading that exists
  * every decision block (`**Decision.**` / `**Alternatives.**` /
    `**Why this one.**`, in that order) is complete and in order
  * all three required inline-SVG diagrams have canonical metadata, resolvable
    figure references, and visible text that survived PDF extraction
  * every generated evidence definition survived extraction, and every `[C1]`
    mark and its back-reference became a working PDF link
  * pdfinfo reports a page count

Then reports which page number carries the title, contents, all three required
diagrams, the widest code block, a table, a dense prose page, and the last
page. It only reports page numbers -- rasterizing them is a
separate, manual step (`pdftoppm -f N -l N -png <doc.pdf> page`).

Exit 0 means clean -- prints a one-line "clean: N pages..." summary plus the
sample-page table. Exit 1 means read the PROBLEM: lines on stderr.
"""
from __future__ import annotations

import re
import subprocess
import sys
import zlib
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^##\s+(\d+)\.\s")
XREF_RE = re.compile(r"\b[Ss]ections?\s+(\d+)(?:\s+and\s+(\d+))?")
TABLE_ROW_RE = re.compile(r"^\s*\|")
LEDGER_START = "<!-- evidence-ledger: generated from notes; do not edit -->"
LEDGER_END = "<!-- /evidence-ledger -->"
LEDGER_HEADING_RE = re.compile(r"^##\s+\d+\.\s+Evidence ledger\s*$", re.MULTILINE)
LEDGER_ENTRY_RE = re.compile(
    r'^- <span id="evidence-(?P<id>[A-Z][A-Z0-9_-]*\d+)">'
    r'\*\*\[(?P=id)\] (?P<claim>.+?)\.\*\* '
    r'(?P<kind>cite|derive|measure): (?P<source>.*?)</span>',
    re.MULTILINE,
)
PROSE_ANCHOR_RE = re.compile(
    r'<a id="(?P<anchor>ref-(?P<id>[A-Z][A-Z0-9_-]*)-\d+)" '
    r'href="#evidence-(?P=id)">'
)
DEST_NAME_RE = re.compile(rb"/((?:evidence|ref)-[A-Za-z0-9_-]+)")

# Machine-readable contract with writing.md. Change both ends together.
DECISION_MARKERS = (
    ("Decision", re.compile(r"^\*\*Decision\.\*\*")),
    ("Alternatives", re.compile(r"^\*\*Alternatives\.\*\*")),
    ("Why this one", re.compile(r"^\*\*Why this one\.\*\*")),
)

# Machine-readable contract with diagrams.md and writing.md. The values are
# deliberately semantic rather than presentation names: captions may become
# more specific, while these roles remain stable across every study.
REQUIRED_DIAGRAMS = (
    "implementation-structure",
    "execution-flow",
    "decision-landscape",
)
KNOWN_DIAGRAMS = frozenset(REQUIRED_DIAGRAMS) | {
    "state-machine", "data-layout", "lifecycle", "concurrency",
    "algorithm-stages",
}
DIAGRAM_SAMPLE_NAMES = {
    "implementation-structure": "structure_diagram",
    "execution-flow": "flow_diagram",
    "decision-landscape": "decisions_diagram",
}
# Machine-readable contract with pseudocode.md. A study's algorithm blocks
# are fenced with the literal info string `pseudocode`; the first non-blank
# line names the block, and `refine` marks a block as the expansion of a step
# some other block calls. The step limit is what forces a complex algorithm to
# be refined into named parts instead of written as one unreadable block.
PSEUDOCODE_FENCE_RE = re.compile(r"^(?:```|~~~)pseudocode\s*$")
PSEUDOCODE_HEADER_RE = re.compile(
    r"^(?P<kind>procedure|refine)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
PSEUDOCODE_MAX_STEPS = 20
FIGURE_REF_RE = re.compile(r"\bFigure\s+(\d+)\b")
FIGURE_CAPTION_RE = re.compile(r"^Figure\s+(\d+)\.\s+(.+)$")


class _DiagramParser(HTMLParser):
    """Extract canonical inline-SVG study figures from Markdown raw HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.figures = []
        self.ids = []
        self._figure = None
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "figure" and "study-diagram" in attrs.get("class", "").split():
            self._figure = {
                "attrs": attrs, "svg": None, "title": "", "desc": "",
                "texts": [], "caption": "",
            }
        elif self._figure is not None and tag == "svg":
            self._figure["svg"] = attrs
        elif self._figure is not None and tag in ("title", "desc", "text", "figcaption"):
            self._capture = tag

    def handle_endtag(self, tag):
        if tag == "figure" and self._figure is not None:
            self.figures.append(self._figure)
            self._figure = None
        if tag == self._capture:
            self._capture = None

    def handle_data(self, data):
        if self._figure is None or self._capture is None:
            return
        text = data.strip()
        if not text:
            return
        key = "texts" if self._capture == "text" else (
            "caption" if self._capture == "figcaption" else self._capture
        )
        if key == "texts":
            self._figure[key].append(text)
        else:
            self._figure[key] += (" " if self._figure[key] else "") + text


def _outside_fences(md_text: str) -> str:
    """Markdown with fenced examples removed, preserving raw renderable HTML."""
    lines = []
    in_fence = False
    for line in md_text.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def _diagrams(md_text: str) -> tuple[list[dict], list[str]]:
    parser = _DiagramParser()
    parser.feed(_outside_fences(md_text))
    return parser.figures, parser.ids


def diagram_problems(md_text: str) -> list[str]:
    """Return malformed, missing, duplicate, or unreferenced SVG figures."""
    figures, ids = _diagrams(md_text)
    problems = []
    roles = [figure["attrs"].get("data-diagram", "") for figure in figures]
    for role in REQUIRED_DIAGRAMS:
        count = roles.count(role)
        if count == 0:
            problems.append(f"missing required diagram: {role}")
        elif count > 1:
            problems.append(f"duplicate required diagram: {role}")
    for role in roles:
        if role and role not in KNOWN_DIAGRAMS:
            problems.append(f"unknown diagram role: {role}")
    for element_id, count in sorted(Counter(ids).items()):
        if count > 1:
            problems.append(f"duplicate id: {element_id}")

    caption_numbers = []
    for index, figure in enumerate(figures, start=1):
        where = figure["attrs"].get("id", f"diagram {index}")
        svg = figure["svg"]
        if svg is None:
            problems.append(f"{where} missing inline svg")
            continue
        if not svg.get("viewbox"):
            problems.append(f"{where} missing svg viewBox")
        if svg.get("role") != "img":
            problems.append(f'{where} missing svg role="img"')
        labelled = svg.get("aria-labelledby", "").split()
        if len(labelled) != 2 or any(label not in ids for label in labelled):
            problems.append(f"{where} has invalid svg aria-labelledby")
        if not figure["title"]:
            problems.append(f"{where} missing svg title")
        if not figure["desc"]:
            problems.append(f"{where} missing svg desc")
        if not figure["texts"]:
            problems.append(f"{where} has no visible svg text")
        match = FIGURE_CAPTION_RE.match(figure["caption"])
        if not match:
            problems.append(f"{where} has invalid figcaption")
        else:
            caption_numbers.append(int(match.group(1)))
    if caption_numbers != list(range(1, len(caption_numbers) + 1)):
        problems.append("figure captions are not numbered sequentially from 1")

    known = set(caption_numbers)
    # Captions themselves contain "Figure N"; references are valid when every
    # number mentioned anywhere resolves to one of those canonical captions.
    for number in {int(m.group(1)) for m in FIGURE_REF_RE.finditer(md_text)}:
        if number not in known:
            problems.append(f"Figure {number} has no matching figcaption")
    return problems


def evidence_render_problems(md_text: str, pdf_text: str) -> list[str]:
    """Return generated evidence definitions missing from PDF extraction."""
    if LEDGER_START not in md_text or LEDGER_END not in md_text:
        return ["markdown has no generated Evidence ledger"]
    start = md_text.find(LEDGER_START)
    end = md_text.find(LEDGER_END, start)
    if end < 0:
        return ["markdown has an unterminated generated Evidence ledger"]
    block = md_text[start:end]
    if not LEDGER_HEADING_RE.search(block):
        return ["generated Evidence ledger has no numbered heading"]
    normalized_pdf = _normalize_text(_body_text(pdf_text))
    problems = []
    if "Evidence ledger" not in normalized_pdf:
        problems.append("Evidence ledger heading did not survive extraction")
    entries = list(LEDGER_ENTRY_RE.finditer(block))
    if not entries:
        problems.append("generated Evidence ledger has no entries")
    for match in entries:
        rendered_source = match.group("source").replace("`", "")
        expected = _normalize_text(
            f"[{match.group('id')}] {match.group('claim')}. "
            f"{match.group('kind')}: {rendered_source}"
        )
        if expected not in normalized_pdf:
            problems.append(
                "evidence definition did not survive extraction: "
                + match.group("id")
            )
    return problems


def _pdf_destination_names(pdf_bytes: bytes) -> set[bytes]:
    """Every name the PDF uses as a link target or a named destination.

    Chrome writes each `href="#name"` as `/Dest /name` on a link annotation and
    each matching element `id` as a `/name [...]` entry in the document's
    destination dictionary. Both are plain objects today; the compressed
    streams are searched too so a future Chrome that packs them away does not
    silently turn this check into a no-op.
    """
    chunks = [pdf_bytes]
    for match in re.finditer(rb"stream\r?\n", pdf_bytes):
        start = match.end()
        end = pdf_bytes.find(b"endstream", start)
        if end < 0:
            continue
        try:
            chunks.append(zlib.decompress(pdf_bytes[start:end]))
        except zlib.error:
            continue
    names: set[bytes] = set()
    for chunk in chunks:
        names.update(match.group(1) for match in DEST_NAME_RE.finditer(chunk))
    return names


def evidence_link_problems(md_text: str, pdf_bytes: bytes) -> list[str]:
    """Return evidence cross-links that did not become PDF links.

    A `[C1]` a reader cannot click is the defect this catches: the definition
    may be present and still leave them scrolling, which is the whole reason
    the marks are anchored rather than merely printed.

    Only cited IDs are expected to have a destination. Chrome emits a named
    destination for an element id when something links to it, so an uncited
    ledger entry -- which `writing.md` allows on purpose -- legitimately has
    none, and demanding one would report a whole document as broken over
    evidence that simply did not make the final cut.
    """
    anchors = list(PROSE_ANCHOR_RE.finditer(_outside_fences(md_text)))
    cited = {match.group("id") for match in anchors}
    expected = {
        f"evidence-{match.group('id')}".encode()
        for match in LEDGER_ENTRY_RE.finditer(md_text)
        if match.group("id") in cited
    }
    expected.update(match.group("anchor").encode() for match in anchors)
    if not expected:
        return []
    names = _pdf_destination_names(pdf_bytes)
    return [
        f"evidence link target is not reachable in the PDF: {name.decode()}"
        for name in sorted(expected - names)
    ]


def diagram_render_problems(md_text: str, pdf_text: str) -> list[str]:
    """Return visible figure text that did not survive PDF extraction."""
    figures, _ = _diagrams(md_text)
    # Smart punctuation applies here too: a label written `A -- B` or with an
    # apostrophe comes back from the page as an en dash or a curly quote, and
    # comparing raw ASCII reports a label that rendered perfectly as missing.
    haystack = {_normalize_text(line) for line in pdf_text.splitlines()}
    problems = []
    for figure in figures:
        labels = [figure["title"], figure["caption"], *figure["texts"]]
        for label in labels:
            target = _normalize_text(label)
            if target and not any(target in line for line in haystack):
                problems.append(f"diagram text did not survive extraction: {label!r}")
    return problems


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


# pandoc's smart punctuation is on by default, so a `derive: C1 -- reasoning`
# source reaches the page as an en dash and no longer matches the ASCII the
# markdown (and this repository) is written in. Folding the rendered
# typography back to ASCII compares what was said rather than how it was set.
SMART_PUNCTUATION = str.maketrans({
    "\u2013": "--", "\u2014": "---", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...",
})


def _normalize_text(s: str) -> str:
    return _normalize_ws(s.translate(SMART_PUNCTUATION))


def _body_text(pdf_text: str) -> str:
    """The extraction with each page's running footer removed.

    `pdftotext -layout` keeps the page number where it sits on the page, so
    joining the pages splices that number into whatever sentence straddled the
    break. A definition that spans two pages is present and correct and would
    still be reported as missing.
    """
    kept = []
    for page in pages(pdf_text):
        lines = page.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and lines[-1].strip().isdigit():
            lines.pop()
        kept.append("\n".join(lines))
    return "\n".join(kept)


def wrapped_lines(md_text: str, pdf_text: str) -> list[str]:
    """Markdown code lines that do not appear (mod whitespace) in the PDF
    extraction. `pdftotext -layout` reconstructs whitespace runs from glyph
    column positions, not the source's literal space count, so a
    right-aligned comment or trailing annotation can come back with a
    different number of internal spaces even though every word survived
    intact and in order. Comparing on collapsed whitespace, not the raw
    string, is what "verbatim (mod whitespace)" in this module's docstring
    actually means -- comparing only on `.strip()`'d ends is stricter than
    that and flags lines that never wrapped at all.
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


def _pseudocode_blocks(md_text: str) -> list[tuple[int, list[str]]]:
    """(1-indexed fence line, non-blank body lines) per `pseudocode` block."""
    blocks = []
    current = None
    start = 0
    in_fence = False
    for number, line in enumerate(md_text.splitlines(), start=1):
        stripped = line.strip()
        if FENCE_RE.match(stripped):
            if in_fence:
                in_fence = False
                if current is not None:
                    blocks.append((start, current))
                    current = None
            else:
                in_fence = True
                if PSEUDOCODE_FENCE_RE.match(stripped):
                    current, start = [], number
            continue
        if current is not None and stripped:
            current.append(stripped)
    if current is not None:  # an unclosed fence at end of document
        blocks.append((start, current))
    return blocks


def pseudocode_problems(md_text: str) -> list[str]:
    """Return pseudocode blocks that break the pseudocode.md contract:
    a missing or malformed header line, a name defined twice, a block over
    PSEUDOCODE_MAX_STEPS steps, or a `refine` block no other block calls.
    Nothing here requires a study to contain pseudocode at all -- an
    implementation whose control flow is one delegating call earns no block,
    and manufacturing one to satisfy a checker is the failure this skill
    exists to avoid.
    """
    problems = []
    defined = {}
    bodies = []
    for line_no, body in _pseudocode_blocks(md_text):
        if not body:
            problems.append(f"pseudocode block at line {line_no} is empty")
            continue
        header = PSEUDOCODE_HEADER_RE.match(body[0])
        if header is None:
            problems.append(
                f"pseudocode block at line {line_no} does not open with "
                "`procedure <name>(...):` or `refine <name>(...):`"
            )
            continue
        name = header.group("name")
        bodies.append((name, body[1:]))
        if name in defined:
            problems.append(
                f"pseudocode block at line {line_no} redefines {name}, "
                f"already defined at line {defined[name][1]}"
            )
            continue
        defined[name] = (header.group("kind"), line_no)
        if len(body) - 1 > PSEUDOCODE_MAX_STEPS:
            problems.append(
                f"pseudocode {name} at line {line_no} has {len(body) - 1} "
                f"steps (limit {PSEUDOCODE_MAX_STEPS}); refine a step into "
                "its own block"
            )
    for name, (kind, line_no) in defined.items():
        if kind != "refine":
            continue
        call = re.compile(rf"\b{re.escape(name)}\s*\(")
        called = any(caller != name and any(call.search(ln) for ln in lines)
                     for caller, lines in bodies)
        if not called:
            problems.append(
                f"refinement {name} at line {line_no} is never called by "
                "another pseudocode block"
            )
    return problems


def incomplete_decision_blocks(md_text: str) -> list[str]:
    """Return incomplete or out-of-order decision blocks outside fences."""
    blocks = []
    current = None
    in_fence = False

    def finish():
        if current is None:
            return
        names = [name for name, _ in current["parts"]]
        missing = [name for name, _ in DECISION_MARKERS if name not in names]
        if missing:
            blocks.append(
                f"decision at line {current['line']} missing: {', '.join(missing)}"
            )
        elif names != [name for name, _ in DECISION_MARKERS]:
            blocks.append(
                f"decision at line {current['line']} has parts out of order"
            )

    for number, line in enumerate(md_text.splitlines(), start=1):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        matched = next(
            (name for name, pattern in DECISION_MARKERS if pattern.match(line)),
            None,
        )
        if matched == "Decision":
            finish()
            current = {"line": number, "parts": [(matched, number)]}
        elif matched is not None:
            if current is not None:
                current["parts"].append((matched, number))
        elif line.startswith("## "):
            finish()
            current = None
    finish()
    return blocks


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
        # Compare on collapsed whitespace, exactly like wrapped_lines: a
        # right-aligned trailing comment is the part of a code line most
        # likely to have its internal spacing repadded by pdftotext's
        # column-position heuristic, so a raw substring check here is the
        # one place this bug bites hardest.
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
    figures, _ = _diagrams(md_text)
    normalized_pages = [_normalize_ws(text) for text in page_texts]
    for figure in figures:
        role = figure["attrs"].get("data-diagram")
        sample_name = DIAGRAM_SAMPLE_NAMES.get(role)
        if sample_name is None:
            continue
        anchors = [figure["title"], figure["caption"]]
        for i, normalized_page in enumerate(normalized_pages, start=1):
            if all(_normalize_ws(anchor) in normalized_page for anchor in anchors):
                result[sample_name] = i
                break
    # Anchor on the first definition, not on the heading: "Evidence ledger" is
    # also a Contents line, and reporting page 1 would send the visual check
    # to the table of contents instead of the ledger it is meant to inspect.
    first = LEDGER_ENTRY_RE.search(md_text)
    if first:
        target = _normalize_text(
            f"[{first.group('id')}] {first.group('claim')}."
        )
        for i, text in enumerate(page_texts, start=1):
            if target in _normalize_text(text):
                result["evidence_ledger"] = i
                break
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
    incomplete = incomplete_decision_blocks(md_text)
    if incomplete:
        problems.append(
            f"{len(incomplete)} incomplete decision block(s): "
            + "; ".join(incomplete[:5])
        )
    pseudocode = pseudocode_problems(md_text)
    if pseudocode:
        problems.append(f"{len(pseudocode)} pseudocode contract problem(s): "
                        + "; ".join(pseudocode[:5]))
    diagrams = diagram_problems(md_text)
    if diagrams:
        problems.append(f"{len(diagrams)} diagram contract problem(s): "
                        + "; ".join(diagrams[:5]))
    rendered_diagrams = diagram_render_problems(md_text, pdf_text)
    if rendered_diagrams:
        problems.append(f"{len(rendered_diagrams)} diagram render problem(s): "
                        + "; ".join(rendered_diagrams[:5]))
    rendered_evidence = evidence_render_problems(md_text, pdf_text)
    if rendered_evidence:
        problems.append(f"{len(rendered_evidence)} evidence render problem(s): "
                        + "; ".join(rendered_evidence[:5]))
    evidence_links = evidence_link_problems(md_text, pdf.read_bytes())
    if evidence_links:
        problems.append(f"{len(evidence_links)} evidence link problem(s): "
                        + "; ".join(evidence_links[:5]))
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
    for name in ("title", "contents", "structure_diagram", "flow_diagram",
                 "decisions_diagram", "evidence_ledger", "widest_code", "table",
                 "prose", "last"):
        if name in samples:
            print(f"  {name:<12} page {samples[name]}")
        else:
            print(f"  {name:<12} (none found)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
