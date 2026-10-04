from pathlib import Path

import check_evidence
from check_evidence import PROSE_REF_RE, parse_ledger

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"

NOTES = """\
# Serving engine -- architecture notes

- [C1] The scheduler owns the batch state. cite: sched.py:41 `self._batch = Batch()`
- [K2] The executor seam leaks a warmup ordering requirement. cite: exec.py:7 `assert self._warm`
- [X3] Every enqueue parks the loop thread. derive: C1, K2 -- the lock guarding the batch is acquired on the loop thread, so a contended enqueue blocks it rather than yielding.
"""


def test_imported_check_evidence_is_this_skills_copy():
    # skills/implementation-study/ ships its own check_evidence.py under the
    # same bare module name; the two are deliberately separate copies.
    assert Path(check_evidence.__file__).resolve() == SKILL_DIR / "check_evidence.py"


def test_parse_ledger_accepts_the_two_classes_this_skill_uses():
    entries = parse_ledger(NOTES)
    assert set(entries) == {"C1", "K2", "X3"}
    assert entries["C1"].kind == "cite"
    assert entries["X3"].kind == "derive"
    # The inventory prefixes survive parsing, so a grown ledger stays
    # navigable by the inventory an ID came from.
    assert entries["K2"].id.startswith("K")


def test_footnote_markers_are_not_read_as_ledger_references():
    # This skill's reports carry a footnote marker for every abbreviation.
    # PROSE_REF_RE treats bracketed uppercase as a citation, so a marker that
    # matched would fail Phase 6 as a reference to an undefined ledger id.
    prose = "The GIL (Global Interpreter Lock)[^gil] serialises it [C1]."
    assert PROSE_REF_RE.findall(prose) == ["C1"]
    assert PROSE_REF_RE.findall("An uppercase tag [^GIL] is still a footnote.") == []


def test_a_bracketed_acronym_would_be_read_as_a_citation():
    # The reason writing.md forbids it: this is indistinguishable from a
    # ledger mark, and the failure surfaces as an undefined-id error.
    assert PROSE_REF_RE.findall("the [GPU] scheduler") == ["GPU"]
