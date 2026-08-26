from pathlib import Path

import check_pdf
from check_pdf import (boundary_problems, glossary_problems,
                       missing_decision_blocks, socratic_problems,
                       spine_problems)

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"

DOC = """\
# Serving engine -- architecture study

## 1. Architectural deconstruction

**Boundary.** Inside: the scheduler and the executor. Excluded: the tokenizer,
which was not read.

The GIL (Global Interpreter Lock)[^gil] shapes the admission path, and the GIL
also bounds the copy.

## 2. Key abstractions and data models

Each batch crosses the seam as I/O (Input/Output)[^io] descriptors.

## 3. Execution lifecycle and data flow

One request, admitted to released.

## 4. Trade-off analysis

**Decision.** Paged blocks.

**Alternatives.** One contiguous arena.

**Why this one.** Fragmentation dominates above a few thousand sessions.

## 5. System constraints and vulnerabilities

The enqueue blocks the loop thread.

## 6. Alternative paradigms

An actor system wins once the participant set is open.

## 7. Guided exploration

- Where does ownership of the batch actually end?
- What would have to be true for the executor seam to cut?

## 8. Sources

None.

## 9. Evidence ledger

Generated.

[^gil]: CPython's interpreter-wide mutex.
[^io]: Transfers crossing a kernel boundary.
"""


def test_imported_check_pdf_is_this_skills_copy():
    # skills/asm-tutorial/ and skills/implementation-study/ each ship a
    # check_pdf.py too, and all three suites import it by bare module name.
    # Only this copy carries the spine and glossary contracts asserted below.
    assert Path(check_pdf.__file__).resolve() == SKILL_DIR / "check_pdf.py"


def test_a_conforming_document_is_clean():
    assert spine_problems(DOC) == []
    assert boundary_problems(DOC) == []
    assert socratic_problems(DOC) == []
    assert glossary_problems(DOC) == []
    assert missing_decision_blocks(DOC) == []
    assert check_pdf.incomplete_decision_blocks(DOC) == []


def test_required_diagram_roles_are_the_architecture_views():
    assert check_pdf.REQUIRED_DIAGRAMS == (
        "system-decomposition", "contract-map", "execution-lifecycle",
        "tradeoff-landscape",
    )
    assert set(check_pdf.DIAGRAM_SAMPLE_NAMES) == set(check_pdf.REQUIRED_DIAGRAMS)
    assert set(check_pdf.REQUIRED_DIAGRAMS) <= check_pdf.KNOWN_DIAGRAMS


def test_retitled_spine_section_is_reported():
    problems = spine_problems(DOC.replace("## 4. Trade-off analysis",
                                          "## 4. Tradeoff analysis"))
    assert len(problems) == 1
    assert "expected 'Trade-off analysis'" in problems[0]


def test_a_gap_in_the_numbering_is_reported():
    # HEADING_RE alone collapses numbers into a set, which has no memory of a
    # gap or a repeat; this is the check that gives the sequence back.
    problems = spine_problems(DOC.replace("## 9. Evidence ledger",
                                          "## 10. Evidence ledger"))
    assert any("no gap or repeat" in p for p in problems)


def test_a_repeated_number_is_reported():
    problems = spine_problems(DOC.replace("## 8. Sources", "## 7. Sources"))
    assert any("no gap or repeat" in p for p in problems)


def test_missing_back_matter_is_reported():
    problems = spine_problems(DOC.replace("## 8. Sources\n\nNone.\n\n", ""))
    assert any("missing back-matter chapter: Sources" in p for p in problems)


def test_missing_and_misplaced_boundary_blocks_are_reported():
    assert "no **Boundary.** block" in boundary_problems(
        DOC.replace("**Boundary.**", "**Scope.**"))[0]
    doubled = DOC.replace("The GIL (Global", "**Boundary.** Again.\n\nThe GIL (Global")
    assert "expected exactly one" in boundary_problems(doubled)[0]
    moved = DOC.replace("**Boundary.** Inside: the scheduler and the executor. Excluded: the tokenizer,\nwhich was not read.\n\n", "")
    moved = moved.replace("One request, admitted to released.",
                          "**Boundary.** Inside: everything.")
    assert "outside section 1" in boundary_problems(moved)[0]


def test_question_count_is_bounded_at_both_ends():
    too_few = DOC.replace(
        "- What would have to be true for the executor seam to cut?\n", "")
    assert "has 1 question item(s)" in socratic_problems(too_few)[0]
    too_many = DOC.replace(
        "## 8. Sources",
        "- A third?\n- A fourth?\n- A fifth?\n\n## 8. Sources")
    assert "has 5 question item(s)" in socratic_problems(too_many)[0]
    # A question mark inside a paragraph is not a question item.
    prose = DOC.replace("One request, admitted to released.",
                        "Where does this end? Nowhere in particular.")
    assert socratic_problems(prose) == []


def test_a_document_with_no_decision_block_is_reported():
    assert missing_decision_blocks(DOC.replace("**Decision.**", "**Choice.**"))


def test_abbreviation_must_be_expanded_and_footnoted_at_first_use():
    bare = DOC.replace("The GIL (Global Interpreter Lock)[^gil] shapes", "The GIL shapes")
    problems = glossary_problems(bare)
    assert any("GIL is used before it is spelled out" in p for p in problems)
    assert any("[^gil] is defined but never used" in p for p in problems)


def test_an_expansion_without_a_footnote_is_reported_precisely():
    problems = glossary_problems(
        DOC.replace("(Global Interpreter Lock)[^gil]", "(Global Interpreter Lock)")
           .replace("[^gil]: CPython's interpreter-wide mutex.\n", ""))
    assert problems == ["line 8: GIL is spelled out but carries no footnote marker"]


def test_a_second_expansion_is_reported():
    problems = glossary_problems(
        DOC.replace("and the GIL\nalso bounds",
                    "and the GIL (Global Interpreter Lock)[^gil]\nalso bounds"))
    assert any("GIL is expanded again" in p for p in problems)


def test_an_expansion_that_does_not_spell_the_term_out_is_reported():
    problems = glossary_problems(
        DOC.replace("(Global Interpreter Lock)", "(Giant Lock)"))
    assert problems == ["line 8: GIL is not spelled out by 'Giant Lock'"]


def test_slashed_abbreviations_are_covered():
    problems = glossary_problems(DOC.replace("I/O (Input/Output)[^io]", "I/O"))
    assert any("I/O is used before it is spelled out" in p for p in problems)


def test_undefined_and_unused_footnotes_are_reported():
    assert any("[^gil] is used but never defined" in p for p in glossary_problems(
        DOC.replace("[^gil]: CPython's interpreter-wide mutex.\n", "")))
    assert any("[^gil] is defined 2 times" in p for p in glossary_problems(
        DOC.replace("[^io]: Transfers", "[^gil]: Again.\n[^io]: Transfers")))


def test_abbreviations_outside_prose_are_exempt():
    # An acronym in a code excerpt, an inline span, an SVG label, or a
    # footnote's own body is not the author introducing a term to a reader.
    for insertion in (
        "```\nHBM DMA\n```",
        "The flag `USE_HBM` is read once.",
        '<figure class="study-diagram" data-diagram="contract-map" id="figure-9">\n'
        '<svg viewBox="0 0 10 10" role="img" aria-labelledby="figure-9-title figure-9-desc">\n'
        '<title id="figure-9-title">T</title><desc id="figure-9-desc">D</desc>\n'
        '<text x="1" y="1" class="diagram-label">HBM</text>\n</svg>\n'
        "<figcaption>Figure 9. Contract map</figcaption>\n</figure>",
    ):
        doc = DOC.replace("One request, admitted to released.", insertion)
        assert glossary_problems(doc) == [], insertion[:20]


def test_generated_ledger_body_is_exempt():
    doc = DOC.replace(
        "## 9. Evidence ledger\n\nGenerated.\n",
        check_pdf.LEDGER_START + "\n## 9. Evidence ledger\n\n"
        "- <span id=\"evidence-C1\">**[C1] The HBM pool is preallocated.** "
        "cite: pool.py:3 `self._hbm = alloc()`</span>\n\n"
        + check_pdf.LEDGER_END + "\n")
    assert glossary_problems(doc) == []
