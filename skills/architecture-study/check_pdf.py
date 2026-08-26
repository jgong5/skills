#!/usr/bin/env python3
"""Verify an architecture study PDF against the markdown it was rendered from.

    <skill-dir>/check_pdf.py <doc.pdf> <doc.md>

Mechanical checks, over every page:
  * every font pdffonts reports is embedded
  * every code line in the markdown appears verbatim (mod whitespace) in the
    pdftotext -layout extraction -- a line that wrapped in the PDF comes back
    split across two lines and fails this
  * the seven fixed spine sections are present, numbered 1 through 7, titled
    verbatim, in order, with no gap or repeat in the numbering that follows
  * exactly one `**Boundary.**` block, and it sits inside section 1
  * every "section N" / "sections N and M" cross-reference in the markdown
    resolves to a "## N." heading that exists
  * at least one decision block, and every decision block (`**Decision.**` /
    `**Alternatives.**` / `**Why this one.**`, in that order) complete
  * section 7 closes on two to four list items, each ending in a question mark
  * every abbreviation is expanded and footnoted at its first occurrence in
    prose, expanded exactly once, and every footnote is defined and used
  * all four required inline-SVG diagrams have canonical metadata, resolvable
    figure references, and visible text that survived PDF extraction
  * every generated evidence definition survived extraction, and every `[C1]`
    mark and its back-reference became a working PDF link
  * pdfinfo reports a page count

Then reports which page number carries the title, contents, all four required
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
    "system-decomposition",
    "contract-map",
    "execution-lifecycle",
    "tradeoff-landscape",
)
KNOWN_DIAGRAMS = frozenset(REQUIRED_DIAGRAMS) | {
    "blocking-path", "alternative-paradigm", "state-machine", "data-layout",
    "memory-lifetime", "concurrency", "failure-modes",
}
DIAGRAM_SAMPLE_NAMES = {
    "system-decomposition": "decomposition",
    "contract-map": "contracts",
    "execution-lifecycle": "lifecycle",
    "tradeoff-landscape": "tradeoffs",
}

# Machine-readable contract with writing.md. The seven section titles are
# fixed and matched verbatim: the report answers the same seven questions
# every time, so a reader who has read one can navigate any other.
SPINE = (
    "Architectural deconstruction",
    "Key abstractions and data models",
    "Execution lifecycle and data flow",
    "Trade-off analysis",
    "System constraints and vulnerabilities",
    "Alternative paradigms",
    "Guided exploration",
)
BACK_MATTER = ("Sources", "Evidence ledger")
HEADING_FULL_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
BOUNDARY_RE = re.compile(r"^\*\*Boundary\.\*\*")
QUESTION_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+.*\?\s*$")
MIN_QUESTIONS, MAX_QUESTIONS = 2, 4

# Machine-readable contract with writing.md's abbreviation rule. An
# abbreviation is a run of two or more uppercase letters and digits, or a
# slashed pair such as I/O; at its first appearance in prose it carries a
# parenthetical expansion and a footnote marker, and never carries one again.
ABBREV_RE = re.compile(r"\b(?:[A-Z](?:/[A-Z])+|[A-Z][A-Z0-9]+)\b")
EXPANSION_RE = re.compile(r"\A \(([^)]{2,})\)\[\^([A-Za-z0-9_-]+)\]")
REDUNDANT_EXPANSION_RE = re.compile(r"\A \([^)]{2,}\)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:", re.MULTILINE)
FOOTNOTE_REF_RE = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HTML_FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.DOTALL | re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>\n]*>")
LEDGER_MARK_RE = re.compile(r"\[[A-Z][A-Z0-9_-]*\]")

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
    """Return pseudocode blocks that break writing.md's contract:
    a missing or malformed header line, a name defined twice, a block over
    PSEUDOCODE_MAX_STEPS steps, or a `refine` block no other block calls.
    Nothing here requires a study to contain pseudocode at all -- a
    traced loop whose control flow is one delegating call earns no block,
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


def _headings(md_text: str) -> list[tuple[int, str]]:
    """Every `## N. Title` heading outside a fenced block, in document order."""
    out = []
    for line in _outside_fences(md_text).splitlines():
        match = HEADING_FULL_RE.match(line)
        if match:
            out.append((int(match.group(1)), match.group(2)))
    return out


def spine_problems(md_text: str) -> list[str]:
    """Return spine sections that are missing, misnumbered, or retitled."""
    headings = _headings(md_text)
    problems = []
    numbers = [number for number, _ in headings]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append("section numbers are not 1..N with no gap or repeat: "
                        + ", ".join(str(number) for number in numbers))
    for index, title in enumerate(SPINE):
        if index >= len(headings):
            problems.append(f"missing spine section {index + 1}. {title}")
        elif headings[index][1] != title:
            problems.append(f"section {index + 1} is titled "
                            f"{headings[index][1]!r}, expected {title!r}")
    tail = [title for _, title in headings[len(SPINE):]]
    for title in BACK_MATTER:
        if title not in tail:
            problems.append(f"missing back-matter chapter: {title}")
    return problems


def _section_bounds(md_text: str, number: int) -> tuple[int, int] | None:
    """Line indices bounding one section of the fence-stripped document."""
    lines = _outside_fences(md_text).splitlines()
    start = None
    for index, line in enumerate(lines):
        match = HEADING_FULL_RE.match(line)
        if not match:
            continue
        if start is None:
            if int(match.group(1)) == number:
                start = index
        else:
            return start, index
    return None if start is None else (start, len(lines))


def boundary_problems(md_text: str) -> list[str]:
    """Return problems with the single `**Boundary.**` block in section 1."""
    lines = _outside_fences(md_text).splitlines()
    marks = [i for i, line in enumerate(lines) if BOUNDARY_RE.match(line)]
    if not marks:
        return ["no **Boundary.** block: the scope is undisclosed"]
    if len(marks) > 1:
        return [f"{len(marks)} **Boundary.** blocks; expected exactly one"]
    bounds = _section_bounds(md_text, 1)
    if bounds is None:
        return []  # spine_problems already reports the missing section
    start, end = bounds
    if not start < marks[0] < end:
        return ["the **Boundary.** block is outside section 1"]
    return []


def socratic_problems(md_text: str) -> list[str]:
    """Return a section 7 that does not close on the right number of questions."""
    bounds = _section_bounds(md_text, len(SPINE))
    if bounds is None:
        return []  # spine_problems already reports the missing section
    lines = _outside_fences(md_text).splitlines()
    start, end = bounds
    count = sum(1 for line in lines[start + 1:end] if QUESTION_ITEM_RE.match(line))
    if not MIN_QUESTIONS <= count <= MAX_QUESTIONS:
        return [f"section {len(SPINE)} has {count} question item(s); expected "
                f"{MIN_QUESTIONS} to {MAX_QUESTIONS}"]
    return []


def missing_decision_blocks(md_text: str) -> list[str]:
    """Return a problem when the trade-off analysis has no decision block."""
    for line in _outside_fences(md_text).splitlines():
        if DECISION_MARKERS[0][1].match(line):
            return []
    return ["no decision block: the trade-off analysis states no decision"]


def _blank(text: str, pattern: re.Pattern) -> str:
    """Replace each match with same-length blanks, preserving line offsets."""
    return pattern.sub(
        lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), text
    )


def _prose_only(md_text: str) -> str:
    """The document with every region that is not authored prose blanked out.

    Offsets survive -- each blanked region keeps its length and its
    newlines -- so a problem is still reportable at the line it occurs on.
    Fenced code, inline code, figure markup, footnote definitions, ledger
    marks, and the generated Evidence ledger all go: an abbreviation inside
    any of them is not the author introducing a term to a reader.
    """
    start = md_text.find(LEDGER_START)
    if start >= 0:
        end = md_text.find(LEDGER_END, start)
        end = len(md_text) if end < 0 else end + len(LEDGER_END)
        blanked = "".join("\n" if c == "\n" else " " for c in md_text[start:end])
        md_text = md_text[:start] + blanked + md_text[end:]

    lines = md_text.splitlines(keepends=True)
    in_fence = in_footnote = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        fence = bool(FENCE_RE.match(stripped))
        if FOOTNOTE_DEF_RE.match(line):
            in_footnote = True
        elif in_footnote and not (stripped and line[:1].isspace()):
            in_footnote = False
        if in_fence or fence or in_footnote:
            lines[index] = "".join(" " if c != "\n" else "\n" for c in line)
        if fence:
            in_fence = not in_fence
    text = "".join(lines)

    for pattern in (HTML_FIGURE_RE, HTML_TAG_RE, INLINE_CODE_RE, LEDGER_MARK_RE):
        text = _blank(text, pattern)
    return text


def _spells_out(abbreviation: str, expansion: str) -> bool:
    """True when the expansion's word initials cover the abbreviation."""
    initials = [word[0].upper() for word in re.findall(r"[A-Za-z]+", expansion)]
    remaining = list(re.sub(r"[^A-Z0-9]", "", abbreviation))
    for initial in initials:
        if remaining and remaining[0] == initial:
            remaining.pop(0)
    return not remaining


def glossary_problems(md_text: str) -> list[str]:
    """Return abbreviations introduced without an expansion and a footnote."""
    prose = _prose_only(md_text)
    problems = []
    first_use: dict[str, int] = {}
    for match in ABBREV_RE.finditer(prose):
        token = match.group(0)
        line = prose.count("\n", 0, match.start()) + 1
        tail = prose[match.end():match.end() + 240]
        expansion = EXPANSION_RE.match(tail)
        if token in first_use:
            if expansion:
                problems.append(f"line {line}: {token} is expanded again; its "
                                f"first use on line {first_use[token]} already "
                                "introduced it")
            continue
        first_use[token] = line
        if not expansion:
            if REDUNDANT_EXPANSION_RE.match(tail):
                problems.append(f"line {line}: {token} is spelled out but "
                                "carries no footnote marker")
            else:
                problems.append(f"line {line}: {token} is used before it is "
                                "spelled out and footnoted")
            continue
        if not _spells_out(token, expansion.group(1)):
            problems.append(f"line {line}: {token} is not spelled out by "
                            f"{expansion.group(1)!r}")

    defined = [m.group(1) for m in FOOTNOTE_DEF_RE.finditer(md_text)]
    referenced = {m.group(1) for m in FOOTNOTE_REF_RE.finditer(_outside_fences(md_text))}
    for tag, count in sorted(Counter(defined).items()):
        if count > 1:
            problems.append(f"footnote [^{tag}] is defined {count} times")
    for tag in sorted(referenced - set(defined)):
        problems.append(f"footnote [^{tag}] is used but never defined")
    for tag in sorted(set(defined) - referenced):
        problems.append(f"footnote [^{tag}] is defined but never used")
    return problems


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
    spine = spine_problems(md_text)
    if spine:
        problems.append(f"{len(spine)} spine problem(s): " + "; ".join(spine[:5]))
    boundary = boundary_problems(md_text)
    if boundary:
        problems.append(f"{len(boundary)} boundary problem(s): "
                        + "; ".join(boundary[:5]))
    socratic = socratic_problems(md_text)
    if socratic:
        problems.append(f"{len(socratic)} guided-exploration problem(s): "
                        + "; ".join(socratic[:5]))
    glossary = glossary_problems(md_text)
    if glossary:
        problems.append(f"{len(glossary)} abbreviation problem(s): "
                        + "; ".join(glossary[:5]))
    broken = broken_xrefs(md_text)
    if broken:
        problems.append(f"{len(broken)} broken cross-reference(s): "
                        + "; ".join(broken[:5]))
    incomplete = missing_decision_blocks(md_text) + incomplete_decision_blocks(md_text)
    if incomplete:
        problems.append(
            f"{len(incomplete)} decision block problem(s): "
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
    for name in ("title", "contents", "decomposition", "contracts", "lifecycle",
                 "tradeoffs", "evidence_ledger", "widest_code", "table",
                 "prose", "last"):
        if name in samples:
            print(f"  {name:<12} page {samples[name]}")
        else:
            print(f"  {name:<12} (none found)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
