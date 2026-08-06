from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "implementation-study"
README = REPO_ROOT / "README.md"
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


def test_writing_documents_how_a_decision_block_renders():
    # Regression: writing.md described a decision block as "exactly three
    # lines" and showed the three markers on adjacent lines. Markdown folds
    # adjacent lines into one paragraph, so a block written that way renders
    # in the PDF as a single run-on paragraph with the three bold labels
    # buried inside it -- mechanically clean (check_pdf.py reads the
    # markdown, never the rendered page) and visually structureless. End-to-
    # end rendering surfaced it; neither checker can. The doc must tell the
    # author to separate the parts with blank lines and say why that is
    # still one block to the checker.
    text = (SKILL_DIR / "writing.md").read_text()
    normalized = _normalize(text)
    assert "blank line between" in normalized
    assert "run-on paragraph" in normalized
    assert "a blank line never closes a block" in normalized
    # The copyable example must itself show the separated form, since that is
    # what an author will paste.
    block = text.split("```markdown\n", 1)[1].split("```", 1)[0]
    assert block.startswith("**Decision.**")
    assert "\n\n**Alternatives.**" in block
    assert "\n\n**Why this one.**" in block


def test_diagram_first_contract_is_documented_across_phases():
    diagrams = (SKILL_DIR / "diagrams.md").read_text()
    writing = (SKILL_DIR / "writing.md").read_text()
    skill = (SKILL_DIR / "SKILL.md").read_text()
    analysis = (SKILL_DIR / "analysis.md").read_text()
    investigation = (SKILL_DIR / "investigation.md").read_text()
    verification = (SKILL_DIR / "verification.md").read_text()

    for role in ("implementation-structure", "execution-flow",
                 "decision-landscape"):
        assert role in diagrams
        assert role in writing
    assert "`<skill-dir>/diagrams.md`" in skill
    assert "visual inventory" in analysis
    assert "decision-landscape figure" in investigation
    assert "Every factual node, edge, transition, and comparison" in writing
    assert "every diagram page" in verification


def test_diagram_contract_matches_checker_roles():
    import check_pdf

    text = (SKILL_DIR / "diagrams.md").read_text()
    for role in check_pdf.REQUIRED_DIAGRAMS:
        assert f'data-diagram="{role}"' in text


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


def test_css_styles_inline_svg_as_a_print_figure():
    css = (SKILL_DIR / "tutorial.css").read_text()
    for selector in ("figure.study-diagram", ".study-diagram svg",
                     ".diagram-node", ".diagram-edge",
                     ".diagram-alternative", "figcaption"):
        assert selector in css
    assert "break-inside: avoid" in css


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


def test_docs_state_the_gitignore_blind_spot_without_promising_a_scan():
    # Regression: both docs described the git integrity pass as proof the
    # repository "came out exactly as it went in". `git status` does not
    # report paths .gitignore excludes and check_evidence.py does not ask it
    # to, so a write into __pycache__/ or a build directory passes in
    # silence. The docs must say so, must not promise an unbaselined scan of
    # ignored files as the answer (it cannot distinguish a file this run
    # created from one that was already there), and must point at the
    # prevention rule in experiments.md instead.
    for name in ("analysis.md", "verification.md"):
        normalized = _normalize((SKILL_DIR / name).read_text())
        assert ".gitignore" in normalized
        assert "__pycache__" in normalized
        assert "unbaselined" in normalized or "no baseline" in normalized \
            or "recorded no baseline" in normalized
        assert "experiments.md" in normalized

    analysis = _normalize((SKILL_DIR / "analysis.md").read_text())
    assert (
        "cannot tell a file this run created from one that was there all "
        "along"
    ) in analysis
    verification = _normalize((SKILL_DIR / "verification.md").read_text())
    assert (
        "rather than describing the repository as byte-for-byte unchanged"
    ) in verification

    # SKILL.md's safety invariant made the same absolute claim.
    skill = _normalize((SKILL_DIR / "SKILL.md").read_text())
    assert "proves, mechanically, that the repository came out exactly" not in skill
    assert "which excludes paths `.gitignore` matches" in skill

    # And so did the checker's own docstring, where the next reader of the
    # code will look first.
    import check_evidence
    docstring = _normalize(check_evidence.check_git_integrity.__doc__)
    assert ".gitignore" in docstring
    assert "__pycache__" in docstring
    assert "Scanning ignored paths is not the fix" in docstring


def test_experiments_requires_suppressing_generated_cache_writes():
    # Regression: nothing told an experiment to stop Python (or any other
    # toolchain) from writing __pycache__/ into the repository under study.
    # Those writes are gitignored, so Phase 5's git pass reports clean --
    # prevention in the wrapper command is the only thing that keeps the
    # read-only promise.
    normalized = _normalize((SKILL_DIR / "experiments.md").read_text())
    assert "PYTHONDONTWRITEBYTECODE=1" in normalized
    assert "__pycache__" in normalized
    assert "part of the wrapper command and environment" in normalized
    assert "`ENV.md`" in normalized
    # Other languages are not optional either.
    assert "Every other language and build system" in normalized


def test_readme_states_the_git_check_boundary_and_the_root_output_rule():
    normalized = _normalize(README.read_text())
    # The old wording claimed the final phase "proves it mechanically",
    # which overpromises for a check that cannot see ignored paths.
    assert "the final phase proves it mechanically" not in normalized
    assert "The git check covers what `git status` covers" in normalized
    assert "does not extend to paths `.gitignore` excludes" in normalized
    assert "PYTHONDONTWRITEBYTECODE=1" in normalized
    # Safety emphasis must survive the qualification.
    assert "**The repository under study is read-only.**" in normalized
    assert (
        "an entry point at the root with no `docs/` above it makes the skill "
        "stop and ask for an output subdirectory rather than write to the root"
    ) in normalized


def test_output_directory_is_never_the_repository_root():
    # Regression: SKILL.md's fallback ("use the entry-point file's own
    # directory") resolved to the repository root for an entry point sitting
    # at the root -- a directory check_evidence.py rejects outright, so the
    # study would run to Phase 5 and fail there. The fallback has to be
    # strictly inside the root, and the degenerate case is a stop-and-ask,
    # not a directory the skill invents.
    skill = _normalize((SKILL_DIR / "SKILL.md").read_text())
    assert "only when that directory is strictly inside the repository root" in skill
    assert (
        "stop and ask the user to name an output subdirectory inside the "
        "repository; do not create one, and do not guess a name"
    ) in skill
    assert (
        "| the entry point sits at the repository root and no ancestor "
        "`docs/` exists |"
    ) in skill

    analysis = _normalize((SKILL_DIR / "analysis.md").read_text())
    assert (
        "The output directory must be strictly inside the repository root, "
        "never the repository root itself."
    ) in analysis
    assert "not to write to the root" in analysis


def test_output_search_never_crosses_the_repository_root():
    # R1 regression: the ancestor `docs/` search had no stated boundary, so a
    # repository with no `docs/` of its own but an ancestor `docs/` outside
    # it (a parent project, a home directory) could be walked into and
    # resolved as the output directory -- a location `check_evidence.py`
    # would eventually reject, but only after Phase 1-4 had already done the
    # work in the wrong place. The repository boundary must govern the walk
    # itself, not just the final `check_evidence.py` gate, and the fallback
    # away from an in-repo `docs/` must be explicit, not silent.
    skill = _normalize((SKILL_DIR / "SKILL.md").read_text())
    assert "never past the repository root" in skill
    assert (
        "an ancestor `docs/` that lies outside the repository is not a "
        "candidate no matter how close it sits to the entry point"
    ) in skill
    assert (
        "never adopted silently: name it to the user and get explicit "
        "approval before Phase 1 does any work"
    ) in skill

    analysis = _normalize((SKILL_DIR / "analysis.md").read_text())
    assert (
        "the walk never crosses the repository root: an ancestor `docs/` "
        "that sits outside the repository is not a candidate"
    ) in analysis
    assert (
        "that fallback is never adopted silently -- it is named to the "
        "user and requires explicit approval before Phase 1 does any work"
    ) in analysis

    readme = _normalize(README.read_text())
    assert (
        "found without crossing the repository boundary -- an ancestor "
        "`docs/` outside the repository is never a candidate"
    ) in readme
    assert "with the user's explicit approval" in readme


def test_rendering_classifies_a_page_tall_block_as_its_own_class():
    # Regression: the render phase knew only about width. A code block taller
    # than the page is a different defect with a different fix -- excerpt or
    # split, never a smaller font -- and tutorial.css's break-inside rule
    # cannot save it.
    normalized = _normalize((SKILL_DIR / "rendering.md").read_text())
    assert "There are four kinds" in normalized
    assert "**A page-tall block.**" in normalized
    assert "The problem here is height, not width." in normalized
    assert "Shrinking the code font is not the fix" in normalized
    assert (
        "Width and height are independent, and finding one tells you nothing "
        "about the other"
    ) in normalized
    assert (
        "every code block taller than a page has been excerpted or split in "
        "the markdown, never resized"
    ) in normalized


def test_verification_does_not_assume_the_widest_page_is_the_tallest():
    # check_pdf.py's sample-page table reports the page with the longest code
    # line and has no notion of block height, so the manual pass must look
    # for a page-tall block separately.
    normalized = _normalize((SKILL_DIR / "verification.md").read_text())
    assert (
        "The table's `widest_code` entry is about width only, and width says "
        "nothing about height"
    ) in normalized
    assert "page-tall class in `rendering.md`" in normalized
    assert "never a smaller code font" in normalized


def test_tutorial_css_break_inside_comment_is_general_purpose():
    # Regression: the comment on `break-inside: avoid` was inherited verbatim
    # from asm-tutorial and asserted "No block in this document is longer
    # than 18 lines" -- a claim about a different document entirely, and
    # false for any study whose excerpts run long. Same for the sibling
    # comment's "73 assembly blocks".
    text = (SKILL_DIR / "tutorial.css").read_text()
    text.encode("ascii")
    # Drop the block comments' leading `*` gutter before normalizing, so a
    # sentence can be pinned without pinning where it wraps.
    normalized = _normalize(
        "\n".join(line.strip().lstrip("*") for line in text.splitlines())
    )
    assert "18 lines" not in normalized
    assert "assembly blocks" not in normalized
    assert "73" not in normalized
    assert "Keep a code block on one page" in normalized
    assert "rendering.md classifies a page-tall block as its own class" in normalized
