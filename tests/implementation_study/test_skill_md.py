import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
LINK_RE = re.compile(r"`<skill-dir>/([\w.-]+)`")


def test_every_skill_dir_reference_resolves():
    text = (SKILL_DIR / "SKILL.md").read_text()
    referenced = set(LINK_RE.findall(text))
    expected = {
        "analysis.md", "investigation.md", "experiments.md", "writing.md",
        "pseudocode.md", "rendering.md", "verification.md", "make_pdf.py",
        "check_pdf.py", "check_evidence.py", "tutorial.css",
    }
    assert expected <= referenced
    missing = [name for name in referenced if not (SKILL_DIR / name).exists()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def test_skill_is_ascii_and_user_invoked_only():
    text = (SKILL_DIR / "SKILL.md").read_text()
    text.encode("ascii")
    assert "disable-model-invocation: true" in text.split("---", 2)[1]
    assert "User-invoked: type /implementation-study." in text


def test_skill_documents_paths_and_five_phases():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for suffix in (
        "_study.md", "_study.notes.md", "_study_experiments/",
        "_study.integrity.json", "_study.pdf",
    ):
        assert suffix in text
    for phase in ("Analyze", "Investigate", "Write", "Render", "Verify"):
        assert phase in text


def test_skill_requires_self_contained_generated_evidence_ledger():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "check_evidence.py materialize-ledger" in text
    assert "terminal Evidence ledger" in text
    assert "understandable inside the PDF itself" in text


def test_skill_documents_requirements_and_degradation():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for tool in ("pandoc", "websockets", "poppler-utils", "Chrome"):
        assert tool in text
    for case in (
        "entry point ambiguous", "no callers", "no canonical form", "no tests",
        "not a git repository", "experiments declined", "generated, vendored, or minified",
        "boundary too large",
    ):
        assert case in text
