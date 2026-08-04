from pathlib import Path

import make_pdf


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
