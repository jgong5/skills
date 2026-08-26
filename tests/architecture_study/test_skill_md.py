import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"
LINK_RE = re.compile(r"`<skill-dir>/([\w.-]+)`")


def flowed():
    """SKILL.md with its hard wrapping collapsed, so a phrase assertion here
    pins the wording rather than where the paragraph happened to break."""
    return " ".join((SKILL_DIR / "SKILL.md").read_text().split())


def test_every_skill_dir_reference_resolves():
    text = (SKILL_DIR / "SKILL.md").read_text()
    referenced = set(LINK_RE.findall(text))
    expected = {
        "survey.md", "paradigms.md", "tracing.md", "weighing.md", "writing.md",
        "diagrams.md", "rendering.md", "verification.md", "make_pdf.py",
        "check_pdf.py", "check_evidence.py", "tutorial.css",
    }
    assert expected <= referenced
    missing = [name for name in referenced if not (SKILL_DIR / name).exists()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def test_skill_is_ascii_and_user_invoked_only():
    text = (SKILL_DIR / "SKILL.md").read_text()
    text.encode("ascii")
    assert "disable-model-invocation: true" in text.split("---", 2)[1]
    assert "User-invoked: type /architecture-study." in text


def test_skill_documents_paths_and_six_phases():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for suffix in ("_architecture.md", "_architecture.notes.md",
                   "_architecture.integrity.json", "_architecture.pdf"):
        assert suffix in text
    for phase in ("Survey", "Trace", "Weigh", "Write", "Render", "Verify"):
        assert f"**{phase}**" in text


def test_skill_carries_the_two_cross_cutting_rules():
    # Altitude calibrates every phase and the witness rule is the whole
    # defence against a fluent review of the system this code resembles.
    # Both are cross-cutting, so both live in SKILL.md rather than in one
    # phase doc that the other phases never load.
    text = flowed()
    assert "## Altitude" in text
    assert "## The witness rule" in text
    assert "whiteboard" in text
    assert "Global Interpreter Lock" in text
    assert "question for section 7, not a finding for section 5" in text


def test_skill_requires_self_contained_generated_evidence_ledger():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "check_evidence.py materialize-ledger" in text
    assert "terminal Evidence ledger" in text


def test_skill_documents_requirements_and_degradation():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for tool in ("pandoc", "websockets", "poppler-utils", "Chrome"):
        assert tool in text
    for case in (
        "the input is one file, not a system",
        "several unrelated systems",
        "too large to read closely",
        "named but never opened",
        "no recognizable paradigm",
        "no single core execution loop",
        "no realistic alternative",
        "no witness",
        "not in a git work tree",
        "generated, vendored, or minified",
    ):
        assert case in text, case


def test_skill_points_a_single_file_input_at_the_sibling_skill():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "/implementation-study" in text
