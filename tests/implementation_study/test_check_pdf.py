from pathlib import Path

import check_pdf
from check_pdf import (code_lines, parse_pdffonts, wrapped_lines, broken_xrefs,
                       pages, sample_pages, incomplete_decision_blocks,
                       diagram_problems, diagram_render_problems,
                       evidence_render_problems, evidence_link_problems,
                       pseudocode_problems)

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"

MD = """\
## 1. Overview

Some prose.

```python
\tqueue.append(item)
\tvisited[node] = distance + weight(node, neighbor)
```

See section 2 for traversal, and sections 3 and 9 for the rest.

## 2. Traversal
"""

PDFFONTS = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
AAAAAA+LiberationSans-Bold           CID TrueType      Identity-H       yes yes yes      4  0
BBBBBB+DejaVuSansMono                CID TrueType      Identity-H       no  yes yes      5  0
"""


def test_imported_check_pdf_is_this_skills_copy():
    # skills/asm-tutorial/ ships a check_pdf.py with most of the same public
    # names. If sys.path or the module cache hands this suite that file, the
    # tests below would silently exercise the wrong skill's code -- see the
    # ordering note in conftest.py for the two orders where that can happen.
    assert Path(check_pdf.__file__).resolve() == SKILL_DIR / "check_pdf.py"


def test_code_lines_extracts_fenced_block_only():
    assert code_lines(MD) == [
        "\tqueue.append(item)",
        "\tvisited[node] = distance + weight(node, neighbor)",
    ]


def test_parse_pdffonts_flags_unembedded():
    assert parse_pdffonts(PDFFONTS) == ["BBBBBB+DejaVuSansMono"]


def test_wrapped_lines_finds_lines_missing_from_extraction():
    pdf_text = "queue.append(item)\n"  # the second line got lost/wrapped
    missing = wrapped_lines(MD, pdf_text)
    assert missing == ["\tvisited[node] = distance + weight(node, neighbor)"]


def test_wrapped_lines_empty_when_everything_present():
    pdf_text = "\n".join(code_lines(MD))
    assert wrapped_lines(MD, pdf_text) == []


def test_wrapped_lines_tolerates_pdftotext_column_repadding():
    # pdftotext -layout reconstructs whitespace runs from glyph column
    # positions, not the source's literal space count -- a right-aligned
    # trailing comment commonly comes back with a different number of
    # internal spaces even though every word survived. This must NOT be
    # reported as wrapped.
    md = "```python\n\tqueue.append(item)      # push onto the frontier\n```\n"
    pdf_text = "  queue.append(item)           # push onto the frontier\n"
    assert wrapped_lines(md, pdf_text) == []


def test_broken_xrefs_flags_missing_sections():
    broken = broken_xrefs(MD)
    joined = " ".join(broken)
    assert "3" in joined and "9" in joined
    assert not any("section 2" in b for b in broken)  # section 2 exists


def test_pages_splits_on_form_feed():
    assert pages("one\ftwo\fthree\f") == ["one", "two", "three"]


def test_sample_pages_reports_title_and_last():
    page_texts = ["Title\n", "Contents\n1. Overview", "body text " * 20]
    samples = sample_pages(MD, page_texts)
    assert samples["title"] == 1
    assert samples["last"] == 3
    assert samples["contents"] == 2


def test_sample_pages_finds_widest_code_despite_repadding():
    md = "## 1. X\n\n```python\n\tqueue.append(item)      # push onto the frontier\n```\n"
    page_texts = ["Title\n", "  queue.append(item)           # push onto the frontier\n"]
    samples = sample_pages(md, page_texts)
    assert samples["widest_code"] == 2


def test_sample_pages_finds_table_page_from_markdown_not_pdf_pipes():
    md = ("## 1. X\n\n"
          "| Constant | Value |\n"
          "| --- | --- |\n"
          "| batch | 64 |\n")
    # Pandoc renders this as an HTML <table> -- no pipe character survives
    # into pdftotext's output, so the table page can only be found by
    # anchoring on a header cell's own words, not on markdown table syntax.
    page_texts = ["Title\n", "Constant   Value\nbatch      64\n"]
    samples = sample_pages(md, page_texts)
    assert samples["table"] == 2


def test_sample_pages_table_detection_skips_fenced_code():
    # An ASCII-art table-like diagram inside a code fence must not be
    # mistaken for a real markdown table.
    md = ("## 1. X\n\n"
          "```text\n"
          "| left | right |\n"
          "```\n\n"
          "| Constant | Value |\n"
          "| --- | --- |\n"
          "| batch | 64 |\n")
    page_texts = ["Title\n", "left   right\n", "Constant   Value\nbatch      64\n"]
    samples = sample_pages(md, page_texts)
    assert samples["table"] == 3


def test_complete_decision_block_passes():
    md = """\
## 6. Main loop

**Decision.** Keep the frontier in a deque.
**Alternatives.** A list with front deletion; two explicit stacks.
**Why this one.** Both end operations are constant time [C8].
"""
    assert incomplete_decision_blocks(md) == []


def test_blank_lines_between_parts_keep_one_complete_block():
    # writing.md tells the author to put a blank line between the three
    # markers so the block does not render as one run-on paragraph. That
    # advice is only safe while a blank line neither closes the open block
    # nor splits it into three incomplete ones, so pin the behavior here:
    # only a `## ` heading or the next `**Decision.**` closes a block.
    md = """\
## 6. Main loop

**Decision.** Keep the frontier in a deque.

**Alternatives.** A list with front deletion; two explicit stacks.

**Why this one.** Both end operations are constant time [C8].

## 7. Improvements
"""
    assert incomplete_decision_blocks(md) == []


def test_decision_block_missing_alternatives_is_reported():
    md = """\
## 6. Main loop

**Decision.** Keep the frontier in a deque.
**Why this one.** Both end operations are constant time [C8].
"""
    problems = incomplete_decision_blocks(md)
    assert len(problems) == 1
    assert "line 3" in problems[0]
    assert "Alternatives" in problems[0]


def test_decision_parts_out_of_order_are_reported():
    md = """\
**Decision.** Keep the frontier in a deque.
**Why this one.** Both end operations are constant time [C8].
**Alternatives.** A list with front deletion.
"""
    assert "order" in incomplete_decision_blocks(md)[0]


def test_markers_inside_code_fences_are_ignored():
    md = """\
```markdown
**Decision.** This is an example, not a real block.
```
"""
    assert incomplete_decision_blocks(md) == []


DIAGRAM_MD = """\
## 1. Overview

<figure class="study-diagram" data-diagram="implementation-structure" id="figure-1">
<svg viewBox="0 0 400 120" role="img" aria-labelledby="figure-1-title figure-1-desc">
<title id="figure-1-title">Implementation structure</title>
<desc id="figure-1-desc">The entry point calls the worker.</desc>
<text x="20" y="40">entry point</text>
<text x="220" y="40">worker</text>
</svg>
<figcaption>Figure 1. Implementation structure</figcaption>
</figure>

Figure 1 shows the call boundary [C1].

<figure class="study-diagram" data-diagram="execution-flow" id="figure-2">
<svg viewBox="0 0 400 120" role="img" aria-labelledby="figure-2-title figure-2-desc">
<title id="figure-2-title">Execution and state flow</title>
<desc id="figure-2-desc">Input becomes output through one state transition.</desc>
<text x="20" y="40">input</text>
<text x="220" y="40">output</text>
</svg>
<figcaption>Figure 2. Execution and state flow</figcaption>
</figure>

Figure 2 explains the transition [C2].

<figure class="study-diagram" data-diagram="decision-landscape" id="figure-3">
<svg viewBox="0 0 400 120" role="img" aria-labelledby="figure-3-title figure-3-desc">
<title id="figure-3-title">Decision landscape</title>
<desc id="figure-3-desc">The chosen queue is compared with an array.</desc>
<text x="20" y="40">queue</text>
<text x="220" y="40">array</text>
</svg>
<figcaption>Figure 3. Decision landscape</figcaption>
</figure>

Figure 3 connects the choice to its constraint [C3].
"""


def test_valid_diagram_contract_passes():
    assert diagram_problems(DIAGRAM_MD) == []


def test_diagram_markup_inside_fenced_example_is_ignored():
    example = "```html\n" + DIAGRAM_MD + "\n```\n"
    problems = " ".join(diagram_problems(example))
    for role in check_pdf.REQUIRED_DIAGRAMS:
        assert f"missing required diagram: {role}" in problems
    assert "duplicate id" not in problems


def test_missing_required_diagram_is_reported():
    md = DIAGRAM_MD.replace(' data-diagram="decision-landscape"',
                            ' data-diagram="lifecycle"')
    problems = " ".join(diagram_problems(md))
    assert "missing required diagram: decision-landscape" in problems


def test_duplicate_ids_and_missing_accessibility_metadata_are_reported():
    md = DIAGRAM_MD.replace('id="figure-2"', 'id="figure-1"', 1)
    md = md.replace(' role="img"', '', 1)
    problems = " ".join(diagram_problems(md))
    assert "duplicate id: figure-1" in problems
    assert "role=\"img\"" in problems


def test_broken_figure_reference_is_reported():
    problems = diagram_problems(DIAGRAM_MD + "\nSee Figure 9.\n")
    assert any("Figure 9" in problem for problem in problems)


def test_diagram_render_check_tolerates_pandoc_smart_punctuation():
    # Same smart-punctuation trap as the evidence check: a label written
    # `one K-stage -- read by the MFMAs` or with an apostrophe comes back from
    # the page as an en dash or a curly quote. Found on a real study, where
    # four labels that rendered perfectly were reported as missing.
    md = DIAGRAM_MD.replace(
        "<text x=\"20\" y=\"40\">entry point</text>",
        "<text x=\"20\" y=\"40\">one K-stage -- the CU's budget</text>",
    )
    pdf_text = md.replace(
        "one K-stage -- the CU's budget",
        "one K-stage \u2013 the CU\u2019s budget",
    )
    assert diagram_render_problems(md, pdf_text) == []


def test_diagram_render_check_reports_missing_visible_svg_text():
    pdf_text = DIAGRAM_MD.replace("worker", "")
    problems = diagram_render_problems(DIAGRAM_MD, pdf_text)
    assert any("worker" in problem for problem in problems)


def test_sample_pages_reports_each_required_diagram():
    page_texts = [
        "Title\n",
        "Implementation structure\nentry point worker\nFigure 1. Implementation structure\n",
        "Execution and state flow\ninput output\nFigure 2. Execution and state flow\n",
        "Decision landscape\nqueue array\nFigure 3. Decision landscape\n",
    ]
    samples = sample_pages(DIAGRAM_MD, page_texts)
    assert samples["structure_diagram"] == 2
    assert samples["flow_diagram"] == 3
    assert samples["decisions_diagram"] == 4


EVIDENCE_MD = """\
## 8. Body

The queue starts with the source <a id="ref-C1-1" href="#evidence-C1">[C1]</a>.

<!-- evidence-ledger: generated from notes; do not edit -->
## 9. Evidence ledger

Each citation ID used above is defined here.

- <span id="evidence-C1">**[C1] The queue starts with the source.** cite: algo.py:1 `queue = [source]`</span> (cited at [1](#ref-C1-1))
- <span id="evidence-D2">**[D2] Append is constant time.** derive: C1 -- deque append does not copy</span>

<!-- /evidence-ledger -->
"""


def test_evidence_render_check_accepts_wrapped_extracted_text():
    pdf_text = (
        "Evidence ledger\n"
        "[C1] The queue starts with the source. cite: algo.py:1\n"
        "queue = [source]\n"
        "[D2] Append is constant time. derive: C1 -- deque append does not copy\n"
    )
    assert evidence_render_problems(EVIDENCE_MD, pdf_text) == []


def test_evidence_render_check_tolerates_pandoc_smart_punctuation():
    # pandoc's smart punctuation is on by default, so a `derive: C1 -- why`
    # source reaches the page as an en dash. End-to-end rendering surfaced
    # this: the definition was present and correct and the check still called
    # it missing.
    pdf_text = (
        "Evidence ledger\n"
        "[C1] The queue starts with the source. cite: algo.py:1 queue = [source]\n"
        "[D2] Append is constant time. derive: C1 \u2013 deque append does not copy\n"
    )
    assert evidence_render_problems(EVIDENCE_MD, pdf_text) == []


def test_evidence_render_check_ignores_a_page_footer_inside_a_definition():
    # A definition that straddles a page break has the running page number
    # spliced into the middle of it by `pdftotext -layout`. Found on a real
    # 25-page study, where three correct definitions were reported missing.
    pdf_text = (
        "Evidence ledger\n"
        "[C1] The queue starts with the source. cite: algo.py:1 queue =\n"
        "16\n\f"
        "[source]\n"
        "[D2] Append is constant time. derive: C1 -- deque append does not copy\n"
    )
    assert evidence_render_problems(EVIDENCE_MD, pdf_text) == []


def test_evidence_render_check_reports_a_missing_definition():
    problems = evidence_render_problems(EVIDENCE_MD, "Evidence ledger\n[C1]\n")
    assert any("C1" in problem for problem in problems)
    assert any("D2" in problem for problem in problems)


def test_sample_pages_reports_the_evidence_ledger_not_the_contents_page():
    # "Evidence ledger" is a Contents line too, so anchoring on the heading
    # sends the visual check to the table of contents. Anchor on a definition.
    page_texts = [
        "Contents\n1. Body\n2. Evidence ledger\n",
        "Body text\n",
        "Evidence ledger\n[C1] The queue starts with the source. cite: algo.py:1\n",
    ]
    samples = sample_pages(EVIDENCE_MD, page_texts)
    assert samples["evidence_ledger"] == 3


def test_evidence_link_check_accepts_reachable_destinations():
    # D2 is in the ledger but no sentence cites it, so Chrome emits no
    # destination for it and none is required -- an unused ledger entry is
    # allowed on purpose. Only C1, which is cited, must be reachable.
    pdf_bytes = (b"/Subtype /Link /Dest /evidence-C1\n"
                 b"/Subtype /Link /Dest /ref-C1-1\n"
                 b"<</evidence-C1 [9 0 R] /ref-C1-1 [2 0 R]>>")
    assert evidence_link_problems(EVIDENCE_MD, pdf_bytes) == []


def test_evidence_link_check_reports_an_unreachable_back_reference():
    pdf_bytes = b"<</evidence-C1 [9 0 R]>>"
    assert evidence_link_problems(EVIDENCE_MD, pdf_bytes) == [
        "evidence link target is not reachable in the PDF: ref-C1-1"
    ]


def test_evidence_link_check_reports_an_unreachable_definition():
    pdf_bytes = b"<</ref-C1-1 [2 0 R]>>"
    assert evidence_link_problems(EVIDENCE_MD, pdf_bytes) == [
        "evidence link target is not reachable in the PDF: evidence-C1"
    ]


def test_evidence_link_check_finds_destinations_inside_compressed_streams():
    # Chrome writes these as plain objects today. If a future version packs
    # them into a compressed object stream, the check must keep looking rather
    # than report every link as broken.
    import zlib

    packed = zlib.compress(b"<</evidence-C1 [9 0 R] /evidence-D2 [9 0 R] "
                           b"/ref-C1-1 [2 0 R]>>")
    pdf_bytes = b"1 0 obj\n<</Filter /FlateDecode>> stream\n" + packed + b"\nendstream"
    assert evidence_link_problems(EVIDENCE_MD, pdf_bytes) == []


PSEUDOCODE_MD = """\
## 1. Traversal

```pseudocode
procedure shortest_paths(graph, source):
    dist <- {source: 0}
    while queue is not empty:
        relax(dist, queue, node, neighbor)
    return dist
```

The frontier is consumed in arrival order [C1].

```pseudocode
refine relax(dist, queue, node, neighbor):
    if neighbor is already in dist:
        return
    dist[neighbor] <- dist[node] + 1
```
"""


def test_refined_pseudocode_passes():
    assert pseudocode_problems(PSEUDOCODE_MD) == []


def test_pseudocode_without_a_header_is_reported():
    md = "```pseudocode\npop the queue\nreturn dist\n```\n"
    problems = pseudocode_problems(md)
    assert len(problems) == 1
    assert "does not open with" in problems[0]


def test_uncalled_refinement_is_reported():
    md = PSEUDOCODE_MD.replace("        relax(dist, queue, node, neighbor)\n", "")
    problems = pseudocode_problems(md)
    assert len(problems) == 1
    assert "refinement relax" in problems[0]
    assert "never called" in problems[0]


def test_self_reference_does_not_count_as_a_call():
    # A refinement that only names itself (a recursive step) is still
    # unreachable from the algorithm the study is explaining.
    md = """```pseudocode
procedure walk(tree):
    return depth

```

```pseudocode
refine descend(node):
    descend(node.left)
```
"""
    problems = pseudocode_problems(md)
    assert len(problems) == 1
    assert "refinement descend" in problems[0]


def test_block_over_the_step_limit_is_reported():
    steps = "\n".join(f"    step {i}" for i in range(check_pdf.PSEUDOCODE_MAX_STEPS + 1))
    md = f"```pseudocode\nprocedure big(x):\n{steps}\n```\n"
    problems = pseudocode_problems(md)
    assert len(problems) == 1
    assert "refine a step into its own block" in problems[0]
    # Exactly at the limit is fine -- the message only fires above it.
    steps = "\n".join(f"    step {i}" for i in range(check_pdf.PSEUDOCODE_MAX_STEPS))
    assert pseudocode_problems(f"```pseudocode\nprocedure big(x):\n{steps}\n```\n") == []


def test_duplicate_block_names_are_reported():
    md = PSEUDOCODE_MD + """
```pseudocode
refine relax(dist, queue, node, neighbor):
    return
```
"""
    problems = pseudocode_problems(md)
    assert len(problems) == 1
    assert "redefines relax" in problems[0]


def test_ordinary_code_fences_are_not_pseudocode_blocks():
    assert pseudocode_problems(MD) == []
    assert pseudocode_problems("```python\ndef f():\n    pass\n```\n") == []


def test_a_study_without_pseudocode_is_not_a_problem():
    # "Where applicable" is the rule: a delegating entry point earns no block,
    # and the checker never demands one.
    assert pseudocode_problems("## 1. Overview\n\nIt delegates.\n") == []
