from pathlib import Path

import make_pdf

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"


def test_imported_make_pdf_is_this_skills_copy():
    # skills/asm-tutorial/ ships a make_pdf.py too, and both suites import it
    # by bare module name. If sys.path or the module cache hands this suite
    # the other skill's file, every assertion below would be testing code this
    # suite does not own -- see the ordering note in conftest.py. Fail loudly
    # here instead.
    assert Path(make_pdf.__file__).resolve() == SKILL_DIR / "make_pdf.py"


def test_docstring_records_why_chrome_is_driven_over_cdp():
    # Regression: this rationale was dropped when the script was forked, and
    # without it the obvious "simplification" is to replace the WebSocket
    # plumbing with chrome --print-to-pdf -- which cannot suppress the URL
    # header without also dropping the page numbers.
    doc = " ".join(make_pdf.__doc__.split())
    assert "Page.printToPDF" in doc
    assert "--print-to-pdf" in doc
    assert "--print-to-pdf-no-header" in doc
    assert "headerTemplate and footerTemplate" in doc
    assert "page numbers with no URL header" in doc


def test_no_args_returns_1(capsys):
    assert make_pdf.main([]) == 1
    assert "usage" in capsys.readouterr().err


def test_missing_file_reports_and_returns_1(capsys):
    assert make_pdf.main(["/tmp/does-not-exist-implementation-study.md"]) == 1
    assert "no such file" in capsys.readouterr().err


def test_css_lives_next_to_script():
    assert make_pdf.CSS.parent == Path(make_pdf.__file__).resolve().parent
    assert make_pdf.CSS.name == "tutorial.css"
    assert make_pdf.CSS.exists()


def test_renders_a_tiny_markdown_to_pdf(tmp_path):
    md = tmp_path / "fixture.md"
    md.write_text("# Fixture\n\n## 1. Section\n\nHello, study.\n")
    chrome = make_pdf.find_chrome()
    pdf = make_pdf.convert(md, chrome)
    assert pdf.exists()
    assert pdf.read_bytes()[:5] == b"%PDF-"
