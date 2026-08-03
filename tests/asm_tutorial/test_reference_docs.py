from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "asm-tutorial"


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def test_analysis_and_writing_are_ascii_and_present():
    for name in ("analysis.md", "writing.md"):
        text = (SKILL_DIR / name).read_text()
        assert _is_ascii(text), f"{name} has non-ASCII characters"
        assert len(text) > 200


def test_writing_states_the_two_hard_rules():
    text = (SKILL_DIR / "writing.md").read_text()
    assert "Derive or cite, never guess" in text
    assert "assembly is the subject" in text
