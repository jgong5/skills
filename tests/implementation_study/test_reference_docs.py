from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
DOCS = (
    "analysis.md", "investigation.md", "experiments.md", "writing.md",
    "rendering.md", "verification.md",
)


def _normalize(text):
    # Collapses all whitespace (line wraps, indentation, blank lines) to a
    # single space, so a sentence's exact wording can be checked without
    # pinning where the author happened to wrap the line.
    return " ".join(text.split())


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


def test_investigation_escalates_experiments_later_in_this_phase():
    # Regression: investigation.md once said an unresolved trade-off became
    # "a question for Phase 4 to answer by running code" -- wrong, since
    # experiments run inside Phase 2 itself (escalating to experiments.md is
    # a Phase 2 step, per "Escalate unresolved questions to experiments" in
    # this same doc and experiments.md's own "Experiments are how Phase 2
    # answers..." opening line). A naive fix that swapped in "Phase 2" read
    # as Phase 2 posing a question to Phase 2, which is just as confusing --
    # the actual fact is that the question is answered later in this same
    # phase, by escalating to experiments.md, not dispatched to a numbered
    # phase at all. This checks the specific wrong phrasing is gone and the
    # corrected, non-self-referential wording is present, rather than a
    # blanket ban on the substring "Phase 4" (which could otherwise trip on
    # a legitimate future reference, e.g. contrasting this phase with
    # Render).
    text = (SKILL_DIR / "investigation.md").read_text()
    normalized = _normalize(text)
    assert "a question for Phase 4 to answer by running code" not in normalized
    assert "a question for Phase 2 to answer by running code" not in normalized
    assert "answered later in this phase" in normalized


def test_experiments_state_execution_and_reproducibility_rules():
    text = (SKILL_DIR / "experiments.md").read_text()
    assert "executes code from the repository under study" in text
    assert "adds no sandbox" in text
    assert "never a bare interpreter" in text
    assert "A failed experiment is a result" in text


def test_experiments_states_are_verbatim_standalone_sentences():
    # Regression: these three rule sentences used to preserve only the
    # tested substrings above -- one was split across a line wrap, another
    # was lower-cased and buried mid-sentence inside a longer bullet, and
    # the third was joined to its neighbor with a colon instead of ending
    # the sentence -- so a stricter, whitespace-sensitive check on the exact
    # brief wording would have failed even though the looser substring
    # checks above passed. The doc keeps its normal hard-wrapped prose (no
    # >80-column single-line sentences forced in to dodge this check); the
    # test instead normalizes whitespace so the wording is pinned
    # independent of where the author wrapped the line.
    text = (SKILL_DIR / "experiments.md").read_text()
    normalized = _normalize(text)
    assert (
        "This executes code from the repository under study and adds no "
        "sandbox beyond not writing to it."
    ) in normalized
    assert (
        "Run through the project's command wrapper, never a bare "
        "interpreter."
    ) in normalized
    assert "A failed experiment is a result." in normalized


def test_writing_places_decision_and_check_pdf_checks_in_phase_five():
    # Regression: writing.md twice said check_pdf.py / the decision-block
    # check ran "in Phase 4" -- wrong, since verification.md's Pass 1 is
    # what runs check_pdf.py, and Pass 1 through Pass 3 are all Phase 5
    # (Verify). Phase 4 is Render, which never invokes check_pdf.py or
    # check_evidence.py. This pins both corrected occurrences and checks
    # the specific wrong phrasing is gone, without banning "Phase 4"
    # outright -- the doc legitimately mentions Phase 4 elsewhere (e.g. its
    # own exit criteria, "Do not move to Phase 4 until...").
    text = (SKILL_DIR / "writing.md").read_text()
    normalized = _normalize(text)
    assert (
        "not just a human: `check_pdf.py` and `check_evidence.py`, "
        "both in Phase 5."
    ) in normalized
    assert (
        "a label the regex does not match makes the whole block "
        "invisible to Phase 5, not just cosmetically different."
    ) in normalized
    assert "check_pdf.py` in Phase 4" not in normalized
    assert "invisible to Phase 4" not in normalized


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


def test_experiments_binds_experiments_dir_to_the_resolved_output_path():
    # Regression: experiments.md used `<experiments-dir>` throughout without
    # ever stating what it actually resolves to, leaving a reader to guess
    # whether it was a placeholder this doc invented or the same path
    # SKILL.md resolves in Phase 1. Both files must say so explicitly.
    exp_text = (SKILL_DIR / "experiments.md").read_text()
    assert "`<experiments-dir>` below is `<stem>_study_experiments/`" in exp_text

    skill_text = (SKILL_DIR / "SKILL.md").read_text()
    normalized_skill = _normalize(skill_text)
    assert (
        "`<skill-dir>/experiments.md` refers to this path as "
        "`<experiments-dir>`."
    ) in normalized_skill


def test_verification_documents_poppler_preflight():
    # Regression: check_pdf.py's poppler-utils dependency (pdftotext,
    # pdffonts, pdfinfo, pdftoppm) was never surfaced as a preflight check
    # anywhere, unlike make_pdf.py's Chrome/pandoc/websockets checks in
    # Phase 4 -- a missing tool would only surface as a raw, uncaught error.
    # Both the phase doc and SKILL.md's degradation table must name the
    # specific missing-tool behavior.
    verification_text = (SKILL_DIR / "verification.md").read_text()
    assert "## Preflight" in verification_text
    assert "poppler-utils" in verification_text
    for tool in ("pdftotext", "pdffonts", "pdfinfo", "pdftoppm"):
        assert tool in verification_text
    normalized_verification = _normalize(verification_text)
    assert (
        "stop and name the specific missing tool and the "
        "`poppler-utils` package that provides it"
    ) in normalized_verification

    skill_text = (SKILL_DIR / "SKILL.md").read_text()
    normalized_skill = _normalize(skill_text)
    assert (
        "a `poppler-utils` tool (`pdftotext`, `pdffonts`, `pdfinfo`, "
        "`pdftoppm`) is missing at Verify preflight"
    ) in normalized_skill
    assert (
        "Stop and name the specific missing tool and the "
        "`poppler-utils` package that provides it"
    ) in normalized_skill


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
