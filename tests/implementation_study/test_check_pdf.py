from pathlib import Path

import check_pdf
from check_pdf import (code_lines, parse_pdffonts, wrapped_lines, broken_xrefs,
                       pages, sample_pages, incomplete_decision_blocks)

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
