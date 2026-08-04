from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
DOCS = (
    "analysis.md", "investigation.md", "experiments.md", "writing.md",
    "rendering.md", "verification.md",
)


def test_reference_docs_are_ascii_and_substantive():
    for name in DOCS:
        path = SKILL_DIR / name
        assert path.exists(), f"missing {name}"
        text = path.read_text()
        text.encode("ascii")
        assert len(text) > 500


def test_analysis_states_integrity_and_omission_rules():
    text = (SKILL_DIR / "analysis.md").read_text()
    assert "Cite, derive, measure, or omit" in text
    assert "modifies or deletes nothing" in text
    assert "check_evidence.py snapshot" in text


def test_investigation_keeps_experiments_behind_approval():
    text = (SKILL_DIR / "investigation.md").read_text()
    assert "read `<skill-dir>/experiments.md`" in text
    assert "approved PLAN.md" in text
    assert "Approval is per-plan" in text


def test_investigation_escalates_to_phase_two_not_phase_four():
    # Regression: investigation.md once said an unresolved trade-off became
    # "a question for Phase 4 to answer by running code", but experiments
    # run inside Phase 2 (escalating to experiments.md is a Phase 2 step,
    # per "Escalate unresolved questions to experiments" in this same doc
    # and experiments.md's own "Experiments are how Phase 2 answers..."
    # opening line). Phase 4 is Render and never runs experiments.
    text = (SKILL_DIR / "investigation.md").read_text()
    assert "Phase 4" not in text
    assert "a question for Phase 2" in text
    assert "to answer by running code" in text


def test_experiments_state_execution_and_reproducibility_rules():
    text = (SKILL_DIR / "experiments.md").read_text()
    assert "executes code from the repository under study" in text
    assert "adds no sandbox" in text
    assert "never a bare interpreter" in text
    assert "A failed experiment is a result" in text


def test_experiments_states_are_verbatim_standalone_sentences():
    # Regression: these two rule sentences used to preserve only the tested
    # substrings above -- one was split across a line wrap, the other was
    # lower-cased and buried mid-sentence inside a longer bullet -- so a
    # stricter, whitespace-sensitive check on the exact brief wording would
    # have failed even though the looser substring checks above passed.
    text = (SKILL_DIR / "experiments.md").read_text()
    assert (
        "This executes code from the repository under study and adds no "
        "sandbox beyond not writing to it."
    ) in text
    assert (
        "Run through the project's command wrapper, never a bare "
        "interpreter."
    ) in text


def test_writing_pins_machine_readable_contracts():
    text = (SKILL_DIR / "writing.md").read_text()
    for marker in ("**Decision.**", "**Alternatives.**", "**Why this one.**"):
        assert marker in text
    assert "- [ID] <claim>. <class>: <source>" in text
    assert "[C1]" in text
    assert "## N. Title" in text
    assert "section N" in text


def test_writing_contains_spine_and_back_matter():
    text = (SKILL_DIR / "writing.md").read_text()
    for title in (
        "What it computes", "Where it sits",
        "Background and the canonical algorithm",
        "How this implementation departs from the canonical form",
        "Data structures and invariants", "Improvements", "Boundary note",
        "Sources",
    ):
        assert title in text
    assert "one to three realistic" in text
    assert "falsifiable" in text


def test_writing_quotes_the_live_checker_regexes():
    # Ties the prose's quoted regexes to the actual compiled patterns, so a
    # future edit to either check_pdf.py or check_evidence.py that changes
    # HEADING_RE, XREF_RE, or ENTRY_PREFIX_RE without updating writing.md
    # fails here instead of only being caught by a human reviewer.
    import check_evidence
    import check_pdf

    text = (SKILL_DIR / "writing.md").read_text()
    assert check_pdf.HEADING_RE.pattern in text
    assert check_pdf.XREF_RE.pattern in text
    assert check_evidence.ENTRY_PREFIX_RE.pattern in text


def test_writing_documents_near_miss_ledger_bullets_are_silently_ignored():
    text = (SKILL_DIR / "writing.md").read_text()
    assert "near-miss" in text
    assert "vanishes from the ledger without a trace" in text
    for example in ("* [C1] ...", "-  [C1] ...", "- [c1] ..."):
        assert example in text


def test_writing_separates_numbering_convention_from_enforcement():
    text = (SKILL_DIR / "writing.md").read_text()
    assert "not something either checker verifies" in text
    assert "a set has no memory of gaps or duplicates" in text


def test_rendering_keeps_margin_css_arithmetic_coupled():
    text = (SKILL_DIR / "rendering.md").read_text()
    assert "N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)" in text
    assert "tutorial.css" in text and "MARGIN_X" in text
    assert "project's command wrapper" in text


def test_verification_states_three_passes_and_failure_routing():
    text = (SKILL_DIR / "verification.md").read_text()
    for item in ("check_pdf.py", "check_evidence.py", "manual read-through"):
        assert item in text
    assert "Phase 1 or Phase 2" in text
    assert "Phase 3 or tutorial.css" in text
    assert "missing citations" in text
