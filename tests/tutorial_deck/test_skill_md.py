import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "tutorial-deck"
LINK_RE = re.compile(r"`<skill-dir>/([\w./-]+)`")


def skill_md():
    return (SKILL_DIR / "SKILL.md").read_text()


def test_every_skill_dir_reference_resolves():
    referenced = set(LINK_RE.findall(skill_md()))
    expected = {
        "surveying.md", "interviewing.md", "outlining.md", "teaching.md",
        "building.md", "verification.md", "revision.md", "deckkit.js",
        # The replay runs under the sibling skill's rules; both ship in
        # code-study, so this path holds wherever the bundle is installed.
        "../implementation-study/experiments.md",
    }
    assert expected <= referenced
    missing = [name for name in referenced if not (SKILL_DIR / name).is_file()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def test_every_file_in_the_skill_is_ascii():
    files = [p for p in SKILL_DIR.rglob("*") if p.is_file()]
    assert SKILL_DIR / "SKILL.md" in files
    for path in files:
        path.read_bytes().decode("ascii")


def test_skill_is_user_invoked_only():
    text = skill_md()
    frontmatter = text.split("---", 2)[1]
    assert "name: tutorial-deck" in frontmatter
    assert "disable-model-invocation: true" in frontmatter
    assert "User-invoked: type /tutorial-deck." in frontmatter
