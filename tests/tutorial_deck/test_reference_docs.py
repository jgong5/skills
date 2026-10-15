import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "tutorial-deck"
CHECKLIST_ITEM_RE = re.compile(r"^\d+\. \*\*(.+?)\.\*\*", re.MULTILINE)
PLAN_FIELD_RE = re.compile(r"^([A-Z][A-Za-z -]*): ", re.MULTILINE)
RULE_ID_RE = re.compile(r"^## R(\d+)\. ", re.MULTILINE)
SELF_CHECK_ID_RE = re.compile(r"^- \*\*R(\d+)\.\*\*", re.MULTILINE)


def section(name, start, end):
    text = (SKILL_DIR / name).read_text()
    return text[text.index(start):text.index(end)]


def test_plan_template_has_one_field_per_checklist_item():
    # The interview writes plan.md from this template; an item without a
    # field is decided and then lost, a field without an item is never asked.
    checklist = section("interviewing.md", "## Decision checklist", "## Interview defaults")
    template = section("interviewing.md", "## `plan.md` template", "Show the finished")
    items = CHECKLIST_ITEM_RE.findall(checklist)
    fields = PLAN_FIELD_RE.findall(template)
    assert items and fields == items


def test_rule_ids_are_unique_and_contiguous():
    # Reviewers cite these IDs; a gap or a duplicate makes a citation ambiguous.
    ids = [int(n) for n in RULE_ID_RE.findall((SKILL_DIR / "teaching.md").read_text())]
    assert ids == list(range(1, len(ids) + 1))


def test_outline_self_check_walks_every_rule():
    checks = section("outlining.md", "## Self-check", "## The replay script")
    ids = [int(n) for n in RULE_ID_RE.findall((SKILL_DIR / "teaching.md").read_text())]
    assert [int(n) for n in SELF_CHECK_ID_RE.findall(checks)] == ids
