from check_pdf import (code_lines, parse_pdffonts, wrapped_lines, broken_xrefs,
                       pages, sample_pages)

MD = """\
## 1. Overview

Some prose.

```asm
\ts_waitcnt lgkmcnt(0)
\tv_mfma_f32_16x16x16_f16 a[0:3], v[2:3], v[4:5], a[0:3]
```

See section 2 for tiling, and sections 3 and 9 for the rest.

## 2. Tiling
"""

PDFFONTS = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
AAAAAA+LiberationSans-Bold           CID TrueType      Identity-H       yes yes yes      4  0
BBBBBB+DejaVuSansMono                CID TrueType      Identity-H       no  yes yes      5  0
"""


def test_code_lines_extracts_fenced_block_only():
    assert code_lines(MD) == [
        "\ts_waitcnt lgkmcnt(0)",
        "\tv_mfma_f32_16x16x16_f16 a[0:3], v[2:3], v[4:5], a[0:3]",
    ]


def test_parse_pdffonts_flags_unembedded():
    assert parse_pdffonts(PDFFONTS) == ["BBBBBB+DejaVuSansMono"]


def test_wrapped_lines_finds_lines_missing_from_extraction():
    pdf_text = "s_waitcnt lgkmcnt(0)\n"  # the MFMA line got lost/wrapped
    missing = wrapped_lines(MD, pdf_text)
    assert missing == ["\tv_mfma_f32_16x16x16_f16 a[0:3], v[2:3], v[4:5], a[0:3]"]


def test_wrapped_lines_empty_when_everything_present():
    pdf_text = "\n".join(code_lines(MD))
    assert wrapped_lines(MD, pdf_text) == []


def test_wrapped_lines_tolerates_pdftotext_column_repadding():
    # pdftotext -layout reconstructs whitespace runs from glyph column
    # positions, not the source's literal space count -- a right-aligned
    # comment column (annotate_asm.py's COMMENT_COL padding) commonly comes
    # back with a different number of internal spaces even though every word
    # survived. This must NOT be reported as wrapped.
    md = "```asm\n\tv_mov_b32 v0, v1      ; per-lane move\n```\n"
    pdf_text = "  v_mov_b32 v0, v1           ; per-lane move\n"
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
