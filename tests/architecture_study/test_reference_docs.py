import re
from pathlib import Path

import check_pdf

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"
DOCS = sorted(SKILL_DIR.glob("*.md"))
LINK_RE = re.compile(r"`<skill-dir>/([\w.-]+)`")
SPINE_LINE_RE = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)


def flowed(name):
    return " ".join((SKILL_DIR / name).read_text().split())


def test_every_tracked_doc_is_ascii():
    for doc in DOCS:
        doc.read_text().encode("ascii")


def test_every_phase_doc_exists_and_is_reachable_from_the_skill():
    assert {doc.name for doc in DOCS} == {
        "SKILL.md", "survey.md", "paradigms.md", "tracing.md", "weighing.md",
        "writing.md", "diagrams.md", "rendering.md", "verification.md",
    }


def test_every_skill_dir_reference_in_every_doc_resolves():
    for doc in DOCS:
        for name in LINK_RE.findall(doc.read_text()):
            assert (SKILL_DIR / name).exists(), f"{doc.name} -> {name}"


def test_writing_md_lists_the_spine_check_pdf_enforces():
    # check_pdf.SPINE matches these titles character for character. Reword one
    # end without the other and the checker stops enforcing what the prose
    # tells the author to write.
    block = (SKILL_DIR / "writing.md").read_text()
    block = block[block.index("## Fixed spine"):block.index("**Section 1**")]
    listed = SPINE_LINE_RE.findall(block)
    assert [title for _, title in listed[:len(check_pdf.SPINE)]] == list(check_pdf.SPINE)
    assert [title for _, title in listed[len(check_pdf.SPINE):]] == list(check_pdf.BACK_MATTER)
    assert [int(n) for n, _ in listed] == list(range(1, len(listed) + 1))


def test_writing_md_quotes_the_decision_markers_verbatim():
    text = (SKILL_DIR / "writing.md").read_text()
    for label, _ in check_pdf.DECISION_MARKERS:
        assert f"**{label}.**" in text


def test_writing_md_states_the_abbreviation_contract():
    text = flowed("writing.md")
    assert "(Global Interpreter Lock)[^gil]" in text
    assert "Never put an acronym in square brackets." in text
    assert "no later occurrence may be expanded again" in text
    # The endnote placement is a Chrome limitation, not a defect to chase.
    assert "no support for paged-media footnotes" in text


def test_writing_md_bounds_the_guided_exploration_close():
    text = flowed("writing.md")
    assert f"{check_pdf.MIN_QUESTIONS} to {check_pdf.MAX_QUESTIONS} questions" in text


def test_writing_md_documents_the_pseudocode_step_limit():
    text = flowed("writing.md")
    assert f"at most {check_pdf.PSEUDOCODE_MAX_STEPS} steps" in text
    assert "procedure Name(args):" in text
    assert "refine Name(args):" in text


def test_diagrams_md_names_every_required_role():
    text = (SKILL_DIR / "diagrams.md").read_text()
    for role in check_pdf.REQUIRED_DIAGRAMS:
        assert f'data-diagram="{role}"' in text
    for role in sorted(check_pdf.KNOWN_DIAGRAMS - set(check_pdf.REQUIRED_DIAGRAMS)):
        assert f"`{role}`" in text, role


def test_survey_md_defines_the_ledger_grammar_and_its_two_classes():
    text = flowed("survey.md")
    assert "- [ID] <claim>. <class>: <source>" in text
    assert "cite:" in text and "derive:" in text
    # measure: exists in check_evidence.py and is deliberately unused here --
    # an architecture study reads code, it does not run benchmarks.
    assert "This skill does not use it." in text
    assert "The boundary is exactly the set of files you open and read." in text


def test_tracing_md_requires_a_mechanism_and_a_trigger():
    text = flowed("tracing.md")
    assert "A constraint enters the inventory only with a `path:line`" in text
    assert "A constraint without a trigger is not falsifiable" in text
    assert "true of the world and says nothing about this system" in text
    assert "Global Interpreter Lock" in text


def test_weighing_md_requires_a_condition_not_a_preference():
    text = flowed("weighing.md")
    assert "the condition under which it wins" in text
    assert "is a preference" in text
    assert "Guard against the strawman." in text


def test_paradigms_md_states_the_three_part_witness_test():
    text = (SKILL_DIR / "paradigms.md").read_text()
    for question in ("**Where is the structure?**", "**What varies?**",
                     "**What would break it?**"):
        assert question in text
    assert "## Naming nothing" in text


def test_rendering_md_and_css_carry_the_same_width_arithmetic():
    inequality = "N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)"
    assert inequality in (SKILL_DIR / "rendering.md").read_text()
    assert inequality in (SKILL_DIR / "tutorial.css").read_text()
    assert "MARGIN_X = 21 / 25.4" in (SKILL_DIR / "make_pdf.py").read_text()


def test_verification_md_routes_findings_rather_than_fixing_them():
    text = flowed("verification.md")
    assert "Nothing is fixed at the pass that caught it." in text
    assert "## Route findings to their source" in text
    for sweep in ("witness sweep", "genre sweep", "adjective sweep",
                  "altitude sweep", "close sweep", "page sweep"):
        assert sweep in text


def test_every_phase_doc_opens_with_its_own_phase_number():
    for number, name in enumerate(
        ("survey.md", "tracing.md", "weighing.md", "writing.md",
         "rendering.md", "verification.md"), start=1
    ):
        first = (SKILL_DIR / name).read_text().splitlines()[0]
        assert first.startswith(f"# Phase {number}:"), (name, first)


def test_footnote_chapter_selector_is_element_agnostic():
    # pandoc emits the endnote block as <section class="footnotes"> before 3.x
    # and <aside class="footnotes"> after. An element-qualified selector stops
    # applying across that upgrade and the chapter renders untitled, with no
    # error anywhere to say so.
    css = re.sub(r"/\*.*?\*/", "", (SKILL_DIR / "tutorial.css").read_text(),
                 flags=re.DOTALL)
    assert ".footnotes::before" in css
    assert "section.footnotes" not in css
    assert "aside.footnotes" not in css
