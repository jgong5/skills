import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "asm-tutorial"
LINK_RE = re.compile(r"`<skill-dir>/([\w.-]+)`")


def test_every_skill_dir_reference_resolves():
    text = (SKILL_DIR / "SKILL.md").read_text()
    referenced = set(LINK_RE.findall(text))
    assert referenced, "expected SKILL.md to reference its companion files"
    missing = [name for name in referenced if not (SKILL_DIR / name).exists()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def test_skill_md_is_ascii():
    (SKILL_DIR / "SKILL.md").read_text().encode("ascii")


def test_skill_md_documents_requirements():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for tool in ("pandoc", "websockets", "poppler-utils"):
        assert tool in text
