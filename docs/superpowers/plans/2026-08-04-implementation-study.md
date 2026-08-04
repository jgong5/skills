# Implementation Study Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a user-invoked `implementation-study` skill that turns one algorithm implementation into an evidence-grounded, mechanically checked PDF study without modifying the repository under study.

**Architecture:** The skill is a self-contained sibling of `asm-tutorial`: it forks that skill's Markdown-to-PDF renderer, stylesheet, and PDF checker, then adds an evidence checker and a five-phase Analyze -> Investigate -> Write -> Render -> Verify workflow. A parseable claim ledger connects prose citations to source anchors, derivations, and approved experiment artifacts; git status or a non-git snapshot enforces the no-modification boundary.

**Tech Stack:** Claude Code skill Markdown, Python 3.12 standard library, pytest, pandoc, Chrome/Chromium through CDP and `websockets`, Poppler (`pdftotext`, `pdffonts`, `pdftoppm`, `pdfinfo`), Claude Code marketplace JSON.

## Global Constraints

- The skill is named `implementation-study`, ships in its own marketplace bundle at version `0.1.0`, and has `disable-model-invocation: true`.
- The input is exactly `path/to/file:symbol` or `path/to/file`; `<stem>` is the symbol when present and otherwise the file stem.
- Resolve output to the nearest ancestor containing `docs/`, walking upward from the entry-point file; if none exists, use the entry-point file's directory.
- Create only new files under that one output directory; never modify or delete an existing file in the repository under study.
- Evidence is cite, derive, measure, or omit. There is no inference class.
- Experiments require an approved `PLAN.md` entry before execution, run through the project's command wrapper, and put scripts, copied inputs, output, and `ENV.md` only in `<stem>_study_experiments/`.
- Every tracked repository file must be ASCII; use `--` and straight quotes.
- The five phases are Analyze, Investigate, Write, Render, Verify. Citation failures return to Analyze or Investigate; render/layout failures return to Write or `tutorial.css`.
- `asm-tutorial` and its tests remain unchanged.
- Run Python and pytest only inside `/md1/users/jgong5/gpu_docker` via `./shell.sh`; run git commands through the same wrapper. Run `claude plugin validate` and `claude plugin details` from the skills repository on the host, as required by this repository's manifest workflow.
- Do not commit the pre-existing untracked root `CLAUDE.md`.

---

## File Structure

### New production files

- `skills/implementation-study/SKILL.md` -- entry-point parsing, output resolution, five-phase orchestration, degradation table, requirements, and final checklist.
- `skills/implementation-study/analysis.md` -- Phase 1 boundary tracing, source reading, initial ledger, and integrity baseline.
- `skills/implementation-study/investigation.md` -- Phase 2 decision inventory, alternatives, history/reference research, and experiment escalation.
- `skills/implementation-study/experiments.md` -- approval protocol and reproducible measurement rules, read only when Phase 2 needs measurement.
- `skills/implementation-study/writing.md` -- Phase 3 document spine, prose citation syntax, ledger grammar, headings, cross-references, decision blocks, and back matter.
- `skills/implementation-study/rendering.md` -- Phase 4 rendering and code-width classification procedure.
- `skills/implementation-study/verification.md` -- Phase 5 PDF, evidence, integrity, and manual assertion checks plus failure routing.
- `skills/implementation-study/make_pdf.py` -- self-contained fork of `asm-tutorial/make_pdf.py`; converts Markdown to PDF through pandoc and Chrome CDP.
- `skills/implementation-study/check_pdf.py` -- self-contained fork of `asm-tutorial/check_pdf.py`; adds decision-block completeness checking.
- `skills/implementation-study/check_evidence.py` -- parses the ledger, validates source anchors and derivations, validates approved measurement artifacts, checks prose coverage, and checks repository integrity.
- `skills/implementation-study/tutorial.css` -- self-contained fork of the print stylesheet; retains its filename to make future three-way maintenance diffs easy.

### New tests

- `tests/implementation_study/conftest.py` -- adds the new skill directory to `sys.path`.
- `tests/implementation_study/test_make_pdf.py` -- renderer smoke and dependency behavior.
- `tests/implementation_study/test_check_pdf.py` -- inherited PDF checks and decision-block completeness.
- `tests/implementation_study/test_check_evidence.py` -- ledger parsing, citations, derivations, measurements, prose coverage, and git/non-git integrity.
- `tests/implementation_study/test_reference_docs.py` -- ASCII, presence, and pinned cross-file invariants.
- `tests/implementation_study/test_skill_md.py` -- companion-link resolution, frontmatter, requirements, and output naming.

### Modified files

- `.claude-plugin/marketplace.json` -- add the third, single-skill `implementation-study` bundle.
- `README.md` -- describe three bundles, document install/requirements/safety for the new skill, and update Update, Uninstall, and Layout text.

### Explicitly unchanged

- `skills/asm-tutorial/**`
- `tests/asm_tutorial/**`
- `skills/pr-explain/**`, `skills/pr-review-draft/**`, and `skills/pr-review-dossier/**`

---

### Task 1: Register the Skill Skeleton and Test Import Path

**Files:**
- Create: `skills/implementation-study/SKILL.md`
- Create: `tests/implementation_study/conftest.py`
- Modify: `.claude-plugin/marketplace.json:8-46`

**Interfaces:**
- Consumes: the marketplace convention that a plugin entry with `source: "./"`, `version`, and `skills` is complete.
- Produces: importable test path `skills/implementation-study/`; bundle `implementation-study` with exactly one skill; temporary but valid `SKILL.md` frontmatter for later expansion.

- [ ] **Step 1: Create the pytest import shim**

```python
# tests/implementation_study/conftest.py
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
sys.path.insert(0, str(SKILL_DIR))
```

- [ ] **Step 2: Create the minimal valid skill file**

```markdown
---
name: implementation-study
description: Turn one algorithm implementation into a verified PDF study with every substantive claim cited, derived, or measured. User-invoked: type /implementation-study.
disable-model-invocation: true
---

# Implementation Study

The full workflow is added in Task 9.
```

- [ ] **Step 3: Add the exact bundle entry to the manifest**

Append this object after the `amd-gpu` object in `.claude-plugin/marketplace.json`:

```json
{
  "name": "implementation-study",
  "source": "./",
  "version": "0.1.0",
  "description": "Turn one algorithm implementation into a verified PDF study: what it computes, how it is used, why each choice was made rather than the alternatives, and how it could be improved -- every claim cited, derived, or measured.",
  "category": "engineering",
  "keywords": [
    "algorithm",
    "documentation",
    "tutorial",
    "pdf",
    "code-explanation"
  ],
  "skills": [
    "./skills/implementation-study"
  ]
}
```

- [ ] **Step 4: Validate schema and skill discovery**

Run from `/md1/users/jgong5/skills` on the host:

```bash
claude plugin validate .
claude plugin details implementation-study
```

Expected: validation succeeds; details reports one skill named `implementation-study`. The second command is mandatory because schema validation does not catch a nonexistent skill directory.

- [ ] **Step 5: Commit the skeleton**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add .claude-plugin/marketplace.json skills/implementation-study/SKILL.md tests/implementation_study/conftest.py
./shell.sh git -C /workspace/skills commit -m "Add implementation-study bundle skeleton"
```

---

### Task 2: Fork and Verify the PDF Renderer

**Files:**
- Create: `skills/implementation-study/make_pdf.py`
- Create: `skills/implementation-study/tutorial.css`
- Create: `tests/implementation_study/test_make_pdf.py`

**Interfaces:**
- Consumes: pandoc, a Chrome-family binary, `websockets`, and Markdown paths supplied explicitly by Phase 4.
- Produces: `CSS: Path`; `find_chrome() -> str`; `to_html(md: Path, html: Path) -> None`; `convert(md: Path, chrome: str, keep_html: bool = False) -> Path`; `main(argv: list[str]) -> int`.

- [ ] **Step 1: Write renderer tests before copying implementation**

```python
# tests/implementation_study/test_make_pdf.py
from pathlib import Path

import make_pdf


def test_no_args_returns_1(capsys):
    assert make_pdf.main([]) == 1
    assert "usage" in capsys.readouterr().err


def test_missing_file_reports_and_returns_1(capsys):
    assert make_pdf.main(["/tmp/does-not-exist-implementation-study.md"]) == 1
    assert "no such file" in capsys.readouterr().err


def test_css_lives_next_to_script():
    assert make_pdf.CSS.parent == Path(make_pdf.__file__).resolve().parent
    assert make_pdf.CSS.name == "tutorial.css"
    assert make_pdf.CSS.exists()


def test_renders_a_tiny_markdown_to_pdf(tmp_path):
    md = tmp_path / "fixture.md"
    md.write_text("# Fixture\n\n## 1. Section\n\nHello, study.\n")
    chrome = make_pdf.find_chrome()
    pdf = make_pdf.convert(md, chrome)
    assert pdf.exists()
    assert pdf.read_bytes()[:5] == b"%PDF-"
```

- [ ] **Step 2: Run the tests and confirm the module is absent**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_make_pdf.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'make_pdf'`.

- [ ] **Step 3: Fork the renderer and stylesheet**

Copy `skills/asm-tutorial/make_pdf.py` and `skills/asm-tutorial/tutorial.css` byte-for-byte first. Then make only these renderer documentation changes:

```python
"""Render an implementation study markdown file to PDF.

    <skill-dir>/make_pdf.py <doc.md> [doc2.md ...]

Markdown paths are required. Output lands next to each input as .pdf.
--keep-html leaves the intermediate HTML there too for layout diagnosis.
"""
```

Keep the CDP implementation, `MARGIN_X = 21 / 25.4`, public signatures, dependency checks, and `tutorial.css` filename unchanged. In `tutorial.css`, replace assembly-specific commentary with this contract while preserving the existing rules:

```css
/* Keep this arithmetic synchronized with make_pdf.py's MARGIN_X and with
 * rendering.md. For a document whose longest indivisible code line is N
 * characters, choose code_pt so:
 *
 *   N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)
 *
 * The shipped value is a readable default, not permission to shrink arbitrary
 * source until it fits; rendering.md classifies overlong lines first.
 */
```

- [ ] **Step 4: Run the renderer tests**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_make_pdf.py -v
```

Expected: all four tests pass. If the render test reports no Chrome, run the repository's documented `gpu_docker/install-chrome.sh`, then rerun; do not skip the test and report success.

- [ ] **Step 5: Verify the fork did not accidentally diverge in behavior**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills diff --no-index skills/asm-tutorial/make_pdf.py skills/implementation-study/make_pdf.py
./shell.sh git -C /workspace/skills diff --no-index skills/asm-tutorial/tutorial.css skills/implementation-study/tutorial.css
```

Expected: nonzero diff command status is normal; differences are limited to the intentional generalization comments. No functional renderer code changes.

- [ ] **Step 6: Commit the renderer**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/make_pdf.py skills/implementation-study/tutorial.css tests/implementation_study/test_make_pdf.py
./shell.sh git -C /workspace/skills commit -m "Add implementation-study PDF renderer"
```

---

### Task 3: Fork the PDF Checker and Enforce Decision Blocks

**Files:**
- Create: `skills/implementation-study/check_pdf.py`
- Create: `tests/implementation_study/test_check_pdf.py`

**Interfaces:**
- Consumes: study Markdown and Poppler output.
- Produces: inherited `code_lines`, `parse_pdffonts`, `wrapped_lines`, `broken_xrefs`, `pages`, `sample_pages`, `run`, and `main`; new `incomplete_decision_blocks(md_text: str) -> list[str]`.
- Contract: `writing.md` must use the literal markers `**Decision.**`, `**Alternatives.**`, and `**Why this one.**` in that order. A new `**Decision.**` or a level-2 heading ends the current block.

- [ ] **Step 1: Fork the existing checker tests and add decision-block tests**

Copy `tests/asm_tutorial/test_check_pdf.py` to the new test path. Change assembly examples to generic Python while retaining every inherited behavior test, especially whitespace-collapse and fenced-table detection. Extend its import and append:

```python
from check_pdf import incomplete_decision_blocks


def test_complete_decision_block_passes():
    md = """\
## 6. Main loop

**Decision.** Keep the frontier in a deque.
**Alternatives.** A list with front deletion; two explicit stacks.
**Why this one.** Both end operations are constant time [C8].
"""
    assert incomplete_decision_blocks(md) == []


def test_decision_block_missing_alternatives_is_reported():
    md = """\
## 6. Main loop

**Decision.** Keep the frontier in a deque.
**Why this one.** Both end operations are constant time [C8].
"""
    problems = incomplete_decision_blocks(md)
    assert len(problems) == 1
    assert "line 3" in problems[0]
    assert "Alternatives" in problems[0]


def test_decision_parts_out_of_order_are_reported():
    md = """\
**Decision.** Keep the frontier in a deque.
**Why this one.** Both end operations are constant time [C8].
**Alternatives.** A list with front deletion.
"""
    assert "order" in incomplete_decision_blocks(md)[0]


def test_markers_inside_code_fences_are_ignored():
    md = """\
```markdown
**Decision.** This is an example, not a real block.
```
"""
    assert incomplete_decision_blocks(md) == []
```

- [ ] **Step 2: Run tests and verify the new function is missing**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_check_pdf.py -v
```

Expected: collection fails because `incomplete_decision_blocks` cannot be imported.

- [ ] **Step 3: Fork `check_pdf.py` and implement the structural check**

Copy `skills/asm-tutorial/check_pdf.py`, generalize assembly-only comments, and add:

```python
# Machine-readable contract with writing.md. Change both ends together.
DECISION_MARKERS = (
    ("Decision", re.compile(r"^\*\*Decision\.\*\*")),
    ("Alternatives", re.compile(r"^\*\*Alternatives\.\*\*")),
    ("Why this one", re.compile(r"^\*\*Why this one\.\*\*")),
)


def incomplete_decision_blocks(md_text: str) -> list[str]:
    """Return incomplete or out-of-order decision blocks outside fences."""
    blocks = []
    current = None
    in_fence = False

    def finish():
        if current is None:
            return
        names = [name for name, _ in current["parts"]]
        missing = [name for name, _ in DECISION_MARKERS if name not in names]
        if missing:
            blocks.append(
                f"decision at line {current['line']} missing: {', '.join(missing)}"
            )
        elif names != [name for name, _ in DECISION_MARKERS]:
            blocks.append(
                f"decision at line {current['line']} has parts out of order"
            )

    for number, line in enumerate(md_text.splitlines(), start=1):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        matched = next(
            (name for name, pattern in DECISION_MARKERS if pattern.match(line)),
            None,
        )
        if matched == "Decision":
            finish()
            current = {"line": number, "parts": [(matched, number)]}
        elif matched is not None:
            if current is not None:
                current["parts"].append((matched, number))
        elif line.startswith("## "):
            finish()
            current = None
    finish()
    return blocks
```

In `main`, after `broken_xrefs`, add:

```python
    incomplete = incomplete_decision_blocks(md_text)
    if incomplete:
        problems.append(
            f"{len(incomplete)} incomplete decision block(s): "
            + "; ".join(incomplete[:5])
        )
```

Also add the decision-block check to the module docstring. Preserve `_normalize_ws`; replacing it with `.strip()` reintroduces the known false positive for `pdftotext` column repadding.

- [ ] **Step 4: Run checker tests**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_check_pdf.py -v
```

Expected: inherited and new tests all pass.

- [ ] **Step 5: Commit the checker**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/check_pdf.py tests/implementation_study/test_check_pdf.py
./shell.sh git -C /workspace/skills commit -m "Add decision-aware PDF verification"
```

---

### Task 4: Implement the Evidence and Integrity Checker

**Files:**
- Create: `skills/implementation-study/check_evidence.py`
- Create: `tests/implementation_study/test_check_evidence.py`

**Interfaces:**
- Consumes: repo root, output directory, `<stem>_study.md`, `<stem>_study.notes.md`, optional `<stem>_study.integrity.json`, experiment `PLAN.md`/`ENV.md`, scripts, and outputs.
- Produces:
  - `LedgerEntry(id: str, claim: str, kind: str, source: str, line: int)`.
  - `parse_ledger(text: str) -> dict[str, LedgerEntry]` and raises `EvidenceFormatError` for malformed entries, duplicate IDs, or unknown classes.
  - `check_citations(entries, repo_root) -> list[str]`.
  - `check_derivations(entries) -> list[str]`.
  - `check_measurements(entries, output_dir) -> list[str]`.
  - `check_prose_coverage(prose, entries) -> list[str]` using `[C1]` references outside fenced code.
  - `check_git_integrity(repo_root, output_dir) -> list[str]`.
  - `write_integrity_snapshot(repo_root, output_dir, snapshot_path, cited_paths) -> None`.
  - `extend_integrity_snapshot(repo_root, output_dir, snapshot_path, cited_paths) -> list[str]`; it first verifies the old baseline and refuses to add hashes if anything changed.
  - `check_snapshot_integrity(repo_root, output_dir, snapshot_path) -> list[str]`.
  - `main(argv: list[str]) -> int` with `snapshot`, `extend-snapshot`, and `verify` subcommands.

The CLI is fixed as:

```text
check_evidence.py snapshot --repo-root ROOT --output-dir OUT --snapshot FILE [--cited-file PATH ...]
check_evidence.py extend-snapshot --repo-root ROOT --output-dir OUT --snapshot FILE [--cited-file PATH ...]
check_evidence.py verify STUDY NOTES --repo-root ROOT --output-dir OUT [--snapshot FILE]
```

- [ ] **Step 1: Write parser and citation tests**

```python
# tests/implementation_study/test_check_evidence.py
import json
import subprocess
from pathlib import Path

import pytest

from check_evidence import (
    EvidenceFormatError,
    check_citations,
    check_derivations,
    check_git_integrity,
    check_measurements,
    check_prose_coverage,
    check_snapshot_integrity,
    extend_integrity_snapshot,
    parse_ledger,
    write_integrity_snapshot,
)


def test_parse_ledger_accepts_all_three_classes():
    text = """\
- [C1] The queue begins with the source. cite: algo.py:4 `queue = [source]`
- [C2] Each vertex enters once. derive: C1, C3 -- membership is checked before append
- [C3] The deque variant is faster. measure: bfs_study_experiments/bench.py -> bfs_study_experiments/bench.out
"""
    entries = parse_ledger(text)
    assert list(entries) == ["C1", "C2", "C3"]
    assert entries["C1"].kind == "cite"
    assert entries["C2"].source.startswith("C1, C3")
    assert entries["C3"].kind == "measure"


@pytest.mark.parametrize("line", [
    "- [C1] Missing a class and source.",
    "- [C1] Unsupported. infer: because it looks right",
    "- [C1] Missing anchor. cite: algo.py:4",
])
def test_parse_ledger_rejects_malformed_entries(line):
    with pytest.raises(EvidenceFormatError):
        parse_ledger(line)


def test_parse_ledger_rejects_duplicate_ids():
    with pytest.raises(EvidenceFormatError, match="duplicate C1"):
        parse_ledger("- [C1] One. cite: a.py:1 `x`\n- [C1] Two. cite: a.py:2 `y`\n")


def test_citation_anchor_must_match_cited_line(tmp_path):
    (tmp_path / "algo.py").write_text("zero\nexpected anchor\n")
    entries = parse_ledger("- [C1] Claim. cite: algo.py:1 `expected anchor`\n")
    assert "moved to line 2" in check_citations(entries, tmp_path)[0]


def test_citation_reports_missing_file_and_line(tmp_path):
    missing = parse_ledger("- [C1] Claim. cite: absent.py:1 `x`\n")
    assert "does not exist" in check_citations(missing, tmp_path)[0]
    (tmp_path / "algo.py").write_text("one\n")
    bad_line = parse_ledger("- [C2] Claim. cite: algo.py:9 `one`\n")
    assert "line 9" in check_citations(bad_line, tmp_path)[0]
```

- [ ] **Step 2: Run the focused tests and confirm the module is absent**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_check_evidence.py -k "parse or citation" -v
```

Expected: collection fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement ledger parsing and file-anchor validation**

Use only the standard library. Define these exact regular expressions and data model so `writing.md` can document the same grammar:

```python
ENTRY_RE = re.compile(
    r"^- \[([A-Z][A-Z0-9_-]*)\] (.+?)\. (cite|derive|measure): (.+)$"
)
FILE_CITE_RE = re.compile(
    r"(?P<path>[^\s,:`]+):(?P<start>\d+)(?:-(?P<end>\d+))?\s+`(?P<anchor>[^`]+)`"
)
REFERENCE_RE = re.compile(r"\b([A-Z][A-Z0-9_-]*\d+)\b")
PROSE_REF_RE = re.compile(r"\[([A-Z][A-Z0-9_-]*)\]")
MEASURE_RE = re.compile(r"^(?P<script>\S+)\s+->\s+(?P<output>\S+)$")
PLAN_RE = re.compile(r"^- \[x\] \[(?P<id>[A-Z][A-Z0-9_-]*)\] (?P<script>\S+) -- .+$")


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    claim: str
    kind: str
    source: str
    line: int


class EvidenceFormatError(ValueError):
    pass
```

`parse_ledger` joins indented continuation lines to their preceding entry, requires one of the three classes, requires a backticked anchor for every file citation, and rejects duplicate IDs. `check_citations` validates only `path:line[-line]` citations; commit SHAs and `http://`/`https://`/paper references remain human-checked external citations. Resolve file paths under `repo_root`; reject `..` escapes. Match an anchor against the joined cited line range after collapsing whitespace. If it does not match, search the whole file and report the unique relocated line as `C1: anchor moved to line N`; otherwise report a mismatch.

- [ ] **Step 4: Add derivation, measurement, and prose-coverage tests**

Append:

```python
def test_derivation_references_must_resolve():
    entries = parse_ledger("- [C2] Result. derive: C1 -- therefore result\n")
    assert "unknown ledger id C1" in check_derivations(entries)[0]


def test_derivation_graph_must_be_acyclic():
    entries = parse_ledger(
        "- [C1] One. derive: C2 -- one from two\n"
        "- [C2] Two. derive: C1 -- two from one\n"
    )
    assert "cycle" in check_derivations(entries)[0]


def test_measurement_requires_artifacts_env_and_approved_plan(tmp_path):
    exp = tmp_path / "bfs_study_experiments"
    exp.mkdir()
    (exp / "bench.py").write_text("print('ok')\n")
    (exp / "bench.out").write_text("ok\n")
    (exp / "ENV.md").write_text("OS: test\n")
    (exp / "PLAN.md").write_text("- [x] [C3] bench.py -- compare deque and list; runtime under 10 seconds\n")
    entries = parse_ledger(
        "- [C3] Deque wins. measure: "
        "bfs_study_experiments/bench.py -> bfs_study_experiments/bench.out\n"
    )
    assert check_measurements(entries, tmp_path) == []


def test_measurement_rejects_unapproved_plan_entry(tmp_path):
    exp = tmp_path / "bfs_study_experiments"
    exp.mkdir()
    for name in ("bench.py", "bench.out", "ENV.md"):
        (exp / name).write_text("x\n")
    (exp / "PLAN.md").write_text("- [ ] [C3] bench.py -- declined\n")
    entries = parse_ledger(
        "- [C3] Deque wins. measure: "
        "bfs_study_experiments/bench.py -> bfs_study_experiments/bench.out\n"
    )
    assert "approved PLAN.md" in check_measurements(entries, tmp_path)[0]


def test_every_prose_reference_must_exist_in_ledger():
    entries = parse_ledger("- [C1] One. cite: algo.py:1 `one`\n")
    assert check_prose_coverage("Supported [C1], not [C9].", entries) == [
        "prose references unknown ledger id C9"
    ]


def test_prose_references_inside_fences_are_ignored():
    entries = parse_ledger("- [C1] One. cite: algo.py:1 `one`\n")
    assert check_prose_coverage("```text\n[C9]\n```\nReal [C1].\n", entries) == []
```

- [ ] **Step 5: Implement derivation, measurement, and prose checks**

`check_derivations` extracts ledger IDs only from the source text before the first `--`, reports missing IDs, and performs depth-first search with `visiting` and `visited` sets to report cycles. Require nonempty reasoning after `--`; `derive: C1` alone is invalid.

`check_measurements` must:

1. Parse `script -> output` exactly.
2. Resolve both paths under `output_dir` and reject escapes.
3. Require both regular files.
4. Require the script parent to equal the output parent.
5. Require `ENV.md` and `PLAN.md` in that same experiments directory.
6. Require an approved line exactly matching `- [x] [<ledger-id>] <script-basename> -- <description>`.

`check_prose_coverage` scans outside fenced code and returns one problem for each distinct prose ID absent from the ledger. Unused ledger entries are allowed.

- [ ] **Step 6: Add git and non-git integrity tests**

Append:

```python
def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def test_git_integrity_allows_only_untracked_output_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "algo.py").write_text("one\n")
    _git(repo, "add", "algo.py")
    _git(repo, "commit", "-m", "base")
    out = repo / "docs"
    out.mkdir()
    (out / "algo_study.md").write_text("study\n")
    assert check_git_integrity(repo, out) == []


def test_git_integrity_rejects_tracked_change_and_outside_untracked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "algo.py").write_text("one\n")
    _git(repo, "add", "algo.py")
    _git(repo, "commit", "-m", "base")
    out = repo / "docs"
    out.mkdir()
    (repo / "algo.py").write_text("changed\n")
    (repo / "scratch.txt").write_text("outside\n")
    problems = " ".join(check_git_integrity(repo, out))
    assert "tracked change" in problems
    assert "outside output directory" in problems


def test_snapshot_detects_metadata_and_cited_content_changes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = repo / "docs"
    out.mkdir()
    cited = repo / "algo.py"
    cited.write_text("one\n")
    other = repo / "README"
    other.write_text("read\n")
    snapshot = out / "algo_study.integrity.json"
    write_integrity_snapshot(repo, out, snapshot, [Path("algo.py")])
    assert check_snapshot_integrity(repo, out, snapshot) == []
    cited.write_text("two\n")
    assert "hash changed" in " ".join(check_snapshot_integrity(repo, out, snapshot))


def test_snapshot_ignores_growth_inside_output_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = repo / "docs"
    out.mkdir()
    (repo / "algo.py").write_text("one\n")
    snapshot = out / "algo_study.integrity.json"
    write_integrity_snapshot(repo, out, snapshot, [Path("algo.py")])
    (out / "algo_study.md").write_text("new output\n")
    assert check_snapshot_integrity(repo, out, snapshot) == []


def test_extending_snapshot_refuses_to_launder_prior_change(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = repo / "docs"
    out.mkdir()
    (repo / "a.py").write_text("a\n")
    (repo / "b.py").write_text("b\n")
    snapshot = out / "x.integrity.json"
    write_integrity_snapshot(repo, out, snapshot, [Path("a.py")])
    (repo / "a.py").write_text("changed\n")
    problems = extend_integrity_snapshot(repo, out, snapshot, [Path("b.py")])
    assert "hash changed" in " ".join(problems)
    data = json.loads(snapshot.read_text())
    assert "b.py" not in data["hashes"]
```

- [ ] **Step 7: Implement integrity checks and deterministic snapshots**

`check_git_integrity` runs `git -C ROOT status --porcelain=v1 --untracked-files=all`. Parse the two-character status plus path. Every entry must have status `??`, and its resolved path must be under `output_dir`; report tracked statuses as `tracked change` and other untracked paths as `outside output directory`. Do not call git if `git -C ROOT rev-parse --is-inside-work-tree` fails.

Use this non-git JSON schema with sorted keys and a trailing newline:

```json
{
  "version": 1,
  "root": ".",
  "excluded_output": "docs",
  "files": {
    "algo.py": {"size": 4, "mtime_ns": 1234567890}
  },
  "hashes": {
    "algo.py": "<sha256 hex>"
  }
}
```

Walk regular files recursively without following symlinked directories, exclude `output_dir` completely, store root-relative POSIX paths, `st_size`, and `st_mtime_ns`, and hash cited files with SHA-256 in 1 MiB chunks. `check_snapshot_integrity` reports added/deleted files and size/mtime changes from `files`, then hash changes from `hashes`. `extend_integrity_snapshot` first calls the checker and returns problems without writing if any exist; otherwise it adds hashes for newly cited paths atomically through a sibling temporary file and `Path.replace`.

- [ ] **Step 8: Add CLI orchestration and test it through `main`**

Add tests using temporary study and ledger files to assert `main(["verify", ...])` returns 0 for clean evidence and 1 with `PROBLEM:` lines for a bad anchor. Implement `argparse` subcommands with the exact CLI above. `verify` runs parser, citations, derivations, measurements, prose coverage, then git integrity when ROOT is a git work tree or snapshot integrity when `--snapshot` is supplied. A non-git verify without `--snapshot` is a problem, not a silent skip. Print `clean: N ledger entries verified` on success.

- [ ] **Step 9: Run the complete evidence test file**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_check_evidence.py -v
```

Expected: all tests pass.

- [ ] **Step 10: Commit the evidence checker**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/check_evidence.py tests/implementation_study/test_check_evidence.py
./shell.sh git -C /workspace/skills commit -m "Add implementation evidence verification"
```

---

### Task 5: Write Analyze, Investigate, and Experiment Methodology

**Files:**
- Create: `skills/implementation-study/analysis.md`
- Create: `skills/implementation-study/investigation.md`
- Create: `skills/implementation-study/experiments.md`
- Create: `tests/implementation_study/test_reference_docs.py`

**Interfaces:**
- Consumes: entry-point and output-directory rules from `SKILL.md`; ledger grammar and integrity commands from `check_evidence.py`.
- Produces: Phase 1 boundary and initial ledger; Phase 2 decision inventory and alternatives; optional approved, reproducible measurement artifacts.

- [ ] **Step 1: Write invariant tests first**

```python
# tests/implementation_study/test_reference_docs.py
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


def test_experiments_state_execution_and_reproducibility_rules():
    text = (SKILL_DIR / "experiments.md").read_text()
    assert "executes code from the repository under study" in text
    assert "adds no sandbox" in text
    assert "never a bare interpreter" in text
    assert "A failed experiment is a result" in text
```

The first test intentionally fails until Tasks 5-8 create all six docs; during Task 5, run the focused invariant tests rather than the whole file.

- [ ] **Step 2: Run focused tests and verify they fail**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -k "analysis or investigation or experiments" -v
```

Expected: failures for missing reference docs.

- [ ] **Step 3: Write `analysis.md` with this exact structure and rules**

```markdown
# Phase 1: Analyze

## Safety preflight
## Resolve the entry point and output directory
## Declare the study boundary
## Read contract, tests, callers, and callees
## Build the comprehension ledger
## Establish repository integrity
## Phase 1 exit criteria
```

Under those headings, explicitly require:

- Stop and ask when the entry point is ambiguous; stop for generated, vendored, or minified code.
- Resolve `<stem>` and output paths before creating anything; fail if any target output file already exists because the skill may create but never overwrite.
- Trace signature/docstring/tests, all in-repo callers, nearest public API path, direct dependencies, state and invariants, and relevant history with `git blame`/`git log -L` when available.
- Declare a narrower boundary when honest tracing would otherwise be shallow, and preserve excluded components for the final Boundary note.
- Start `<stem>_study.notes.md` in the parser's exact grammar. Use `[C1]`, `[C2]`, and so on; file claims carry `path:line[-line]` plus a verbatim backticked anchor.
- Include the literal sentence `Cite, derive, measure, or omit.` State that the skill `modifies or deletes nothing` in the repository under study.
- For git, require a clean baseline before skill outputs and later allow only `??` paths inside output. For non-git, run `check_evidence.py snapshot`; when Phase 2 cites a new file, use `extend-snapshot`, which refuses to launder an earlier change.
- Exit only with a resolved boundary, contract evidence, caller map, initial invariants, ledger, and integrity baseline.

- [ ] **Step 4: Write `investigation.md` with this exact structure and rules**

```markdown
# Phase 2: Investigate

## Build the decision inventory
## Name realistic alternatives
## Ground trade-offs
## Use history and external references
## Escalate unresolved questions to experiments
## Phase 2 exit criteria
```

Define a decision as a choice a competent engineer could plausibly make differently and whose difference matters. For each candidate record: implementation choice, one to three concrete alternatives, observable trade-off, evidence IDs, and whether it merits a decision block. Reject vague alternatives. Derive before measuring. If measurement is needed, instruct `read `<skill-dir>/experiments.md`` and do not execute until the matching entry has an `approved PLAN.md` line. Include `Approval is per-plan`; discoveries require amendments. Record declines in PLAN and ledger, then derive or omit.

- [ ] **Step 5: Write `experiments.md` with an exact plan format**

Require each proposed entry to start unchecked:

```markdown
- [ ] [C12] bench_deque.py -- Ground the queue-operation trade-off; run the project wrapper against copied fixtures; under 30 seconds; CPU only; create a scratch venv under this directory.
```

After the user approves that exact experiment, change only `[ ]` to `[x]`. Use `[~]` for declined and `[-]` for superseded so the decision remains auditable. The evidence checker recognizes only `[x]`.

Document the four user responses: approve all, approve a subset, revise, skip. Require copied inputs and alternative implementations under the experiment directory, reproducible scripts, captured `.out` files, and one `ENV.md` per run containing machine, OS, accelerator, runtime/library versions, repository commit SHA when present, date, wrapper command, and installed packages. Require semantic equivalence before timing, warmup, repetitions, spread and repetition count, bounded runtime, and like-for-like inputs. Include the literal statements `This executes code from the repository under study and adds no sandbox beyond not writing to it.`, `Run through the project's command wrapper, never a bare interpreter.`, and `A failed experiment is a result.`

- [ ] **Step 6: Run the focused reference tests**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -k "analysis or investigation or experiments" -v
```

Expected: the three focused invariant tests pass. The aggregate presence test is still expected to fail until Task 8; do not misreport the entire file as passing.

- [ ] **Step 7: Commit the first two phases**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/analysis.md skills/implementation-study/investigation.md skills/implementation-study/experiments.md tests/implementation_study/test_reference_docs.py
./shell.sh git -C /workspace/skills commit -m "Document implementation study analysis"
```

---

### Task 6: Write the Study Document Contract

**Files:**
- Create: `skills/implementation-study/writing.md`
- Modify: `tests/implementation_study/test_reference_docs.py`

**Interfaces:**
- Consumes: Phase 1 ledger and boundary; Phase 2 decision inventory; `check_pdf.py` marker and heading regexes; `check_evidence.py` ledger and `[ID]` regexes.
- Produces: `<stem>_study.md` using numbered level-2 headings, inline `[ID]` evidence references, complete decision blocks, Improvements, Boundary note, and Sources.

- [ ] **Step 1: Add writing-contract tests**

Append:

```python
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
```

- [ ] **Step 2: Run the new tests and verify failure**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -k writing -v
```

Expected: failure because `writing.md` is absent.

- [ ] **Step 3: Write `writing.md` with the machine-readable contracts beside their rationale**

Use these headings:

```markdown
# Phase 3: Write

## Evidence references and claim discipline
## Fixed spine
## Derived middle
## Decision blocks
## Improvements and back matter
## Code excerpts, headings, and cross-references
## Phase 3 exit criteria
```

Specify prose citations as inline `[C1]` references; every substantive contract, behavior, complexity, rationale, and improvement-condition claim gets one or more ledger IDs. Connective prose does not need fake citations. State that unused ledger entries are allowed and the manual read-through catches missing references.

Include the exact ledger grammar `- [ID] <claim>. <class>: <source>` and examples for cite, derive with shown logic after `--`, and measure with `script -> output`. Add a paired comment saying this format and backticked anchors are a machine-readable contract with `check_evidence.py`.

Require the fixed opening order:

1. What it computes -- inputs, outputs, preconditions, postconditions, failures.
2. Where it sits -- real callers, nearest public API path, dependents; say plainly when no callers exist.
3. Background and the canonical algorithm -- only load-bearing concepts, standard name/form, pseudocode, complexity, external source; say plainly when no canonical form exists.
4. How this implementation departs from the canonical form -- deltas, or the design as a whole when bespoke.
5. Data structures and invariants -- state and truths maintained.

The middle follows the implementation's actual structure rather than a universal template. A decision block is exactly:

```markdown
**Decision.** <what the code does>
**Alternatives.** <one to three realistic other choices>
**Why this one.** <cited or derived trade-off with [C1] references>
```

State that the literal markers and order are a machine-readable contract with `check_pdf.py`; labels must not be reworded. Use a block only when a competent engineer could plausibly choose differently and it matters.

Require final chapters Improvements, Boundary note, and Sources. Each improvement says what changes and what must be true for it to win, making it falsifiable. Use `## N. Title` for every numbered section and phrase cross-references as `section N` or `sections N and M`; note the coupling to `HEADING_RE`/`XREF_RE`. Keep code lines readable; do not manually hard-wrap a source line because the PDF checker expects an indivisible line to survive.

- [ ] **Step 4: Run writing-contract tests**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -k writing -v
```

Expected: all writing tests pass.

- [ ] **Step 5: Commit the writing contract**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/writing.md tests/implementation_study/test_reference_docs.py
./shell.sh git -C /workspace/skills commit -m "Define implementation study document contract"
```

---

### Task 7: Write Render and Verify Procedures

**Files:**
- Create: `skills/implementation-study/rendering.md`
- Create: `skills/implementation-study/verification.md`
- Modify: `tests/implementation_study/test_reference_docs.py`

**Interfaces:**
- Consumes: `<stem>_study.md`, ledger, integrity baseline, `make_pdf.py`, `check_pdf.py`, `check_evidence.py`, and `tutorial.css`.
- Produces: `<stem>_study.pdf`; either a clean verification result or a classified finding routed to the correct phase.

- [ ] **Step 1: Add render/verify invariant tests**

Append:

```python
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
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -k "rendering or verification" -v
```

Expected: failures because the two docs are absent.

- [ ] **Step 3: Write `rendering.md`**

Use:

```markdown
# Phase 4: Render

## Preflight
## Classify wide code before changing styles
## Render through the project wrapper
## Inspect the generated artifacts
## Phase 4 exit criteria
```

Require pandoc, `websockets`, and Chrome; stop with the project's Chrome install pointer when available. Invoke `<skill-dir>/make_pdf.py` through the project's command wrapper, never bare `python3`. Before changing CSS, classify each overlong line as reducible excerpt, semantic source line that must remain whole, or accidental prose/table width. Prefer a smaller representative excerpt; only then calculate a code-font adjustment. Include exactly `N * 0.602 * code_pt <= 612 - 2 * (MARGIN_X * 72)` and say `tutorial.css`, `make_pdf.py`'s `MARGIN_X`, and this formula change together. Keep `--keep-html` as the diagnosis path. A render finding is not yet a prose or CSS fix: classify it first.

- [ ] **Step 4: Write `verification.md`**

Use:

```markdown
# Phase 5: Verify

## Pass 1: Mechanical PDF checks
## Pass 2: Evidence and integrity checks
## Pass 3: Manual read-through
## Route findings to their source
## Phase 5 exit criteria
```

Pass 1 runs `check_pdf.py PDF MD` through the wrapper, then rasterizes each reported sample page with `pdftoppm` and inspects title, contents, widest code, table, dense prose, and last page. Pass 2 runs `check_evidence.py verify` with repo root/output dir and `--snapshot` for non-git repositories. Pass 3 is a manual read-through specifically for missing citations and unsupported assertions; state that the checker catches bad references but cannot distinguish every assertion from connective prose. Do not mechanically require fixed-spine headings because canonical sections legitimately degrade.

State the routing literally: citation, derivation, experiment, or integrity findings return to `Phase 1 or Phase 2`; render, wrapping, visual, or cross-reference findings return to `Phase 3 or tutorial.css`. Editing prose to agree with a bad ledger launders the error. After every fix rerun all three passes, not only the failing command.

- [ ] **Step 5: Run all reference-doc tests**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_reference_docs.py -v
```

Expected: all tests pass, including ASCII and substantive-length checks for all six docs.

- [ ] **Step 6: Commit render and verify docs**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/rendering.md skills/implementation-study/verification.md tests/implementation_study/test_reference_docs.py
./shell.sh git -C /workspace/skills commit -m "Document study rendering and verification"
```

---

### Task 8: Complete the Skill Orchestrator and Degradation Behavior

**Files:**
- Modify: `skills/implementation-study/SKILL.md`
- Create: `tests/implementation_study/test_skill_md.py`

**Interfaces:**
- Consumes: all companion files and public script CLIs created in Tasks 2-7.
- Produces: complete user-invoked workflow from entry point to verified PDF.

- [ ] **Step 1: Write orchestrator tests**

```python
# tests/implementation_study/test_skill_md.py
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
LINK_RE = re.compile(r"`<skill-dir>/([\w.-]+)`")


def test_every_skill_dir_reference_resolves():
    text = (SKILL_DIR / "SKILL.md").read_text()
    referenced = set(LINK_RE.findall(text))
    expected = {
        "analysis.md", "investigation.md", "experiments.md", "writing.md",
        "rendering.md", "verification.md", "make_pdf.py", "check_pdf.py",
        "check_evidence.py", "tutorial.css",
    }
    assert expected <= referenced
    missing = [name for name in referenced if not (SKILL_DIR / name).exists()]
    assert not missing, f"SKILL.md references missing files: {missing}"


def test_skill_is_ascii_and_user_invoked_only():
    text = (SKILL_DIR / "SKILL.md").read_text()
    text.encode("ascii")
    assert "disable-model-invocation: true" in text.split("---", 2)[1]
    assert "User-invoked: type /implementation-study." in text


def test_skill_documents_paths_and_five_phases():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for suffix in (
        "_study.md", "_study.notes.md", "_study_experiments/",
        "_study.integrity.json", "_study.pdf",
    ):
        assert suffix in text
    for phase in ("Analyze", "Investigate", "Write", "Render", "Verify"):
        assert phase in text


def test_skill_documents_requirements_and_degradation():
    text = (SKILL_DIR / "SKILL.md").read_text()
    for tool in ("pandoc", "websockets", "poppler-utils", "Chrome"):
        assert tool in text
    for case in (
        "entry point ambiguous", "no callers", "no canonical form", "no tests",
        "not a git repository", "experiments declined", "generated, vendored, or minified",
        "boundary too large",
    ):
        assert case in text
```

- [ ] **Step 2: Run tests and verify the skeleton is insufficient**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_skill_md.py -v
```

Expected: failures for missing references, phases, paths, and requirements.

- [ ] **Step 3: Replace the skeleton body with the complete orchestrator**

Preserve frontmatter, then use these sections:

```markdown
# Implementation Study

## Input
## Resolve the skill directory
## Resolve output paths
## Safety invariant
## Pipeline
## Degradation
## Requirements
## Final checklist
```

Under Input, accept exactly `path/to/file:symbol` or `path/to/file`; stop and ask if ambiguous. `<stem>` is symbol or file stem. Reject generated, vendored, or minified code.

Under skill-directory resolution, first use `${CLAUDE_PLUGIN_ROOT}/skills/implementation-study`; otherwise use the directory from which `SKILL.md` was read. Bind it as `<skill-dir>`. If the project wrapper cannot reach it, copy only the invoked helper into the output directory rather than running a bare host interpreter.

Under output resolution, walk from the entry-point file upward to the nearest ancestor containing `docs/`; use that `docs/`, otherwise the file's directory. List all five output forms. Before work starts, check none exists. State that output files are new and confined there.

Under Pipeline, make each phase read its doc only when reached:

1. Analyze -- read `<skill-dir>/analysis.md`.
2. Investigate -- read `<skill-dir>/investigation.md`; read `<skill-dir>/experiments.md` only when derivation cannot settle a claim.
3. Write -- read `<skill-dir>/writing.md`.
4. Render -- read `<skill-dir>/rendering.md`; it invokes `<skill-dir>/make_pdf.py` and `<skill-dir>/tutorial.css`.
5. Verify -- read `<skill-dir>/verification.md`; it invokes `<skill-dir>/check_pdf.py` and `<skill-dir>/check_evidence.py`.

The degradation table must contain all exact cases asserted by the test and the design-prescribed behavior: ask on ambiguity; report no callers; say no canonical form; derive contract only from available sources when no tests; use snapshot outside git; derive/omit when experiments are declined; stop for generated/vendored/minified code; narrow and disclose an oversized boundary; stop and point to install help for missing Chrome; stop for missing pandoc.

List Python 3, pandoc, Chrome/Chromium, `websockets`, and `poppler-utils`. State that project commands and experiments use the project's wrapper.

The final checklist requires: boundary disclosed; fixed spine present or explicitly degraded; every substantive claim has a ledger ID; every decision has all three literal parts; improvements are falsifiable; experiment approvals/artifacts complete; PDF checker clean; evidence checker clean; sampled pages inspected; no pre-existing file changed or deleted.

- [ ] **Step 4: Run skill tests and the whole new test subtree**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study/test_skill_md.py -v
./shell.sh python3 -m pytest /workspace/skills/tests/implementation_study -q
```

Expected: all new-skill tests pass.

- [ ] **Step 5: Commit the orchestrator**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add skills/implementation-study/SKILL.md tests/implementation_study/test_skill_md.py
./shell.sh git -C /workspace/skills commit -m "Complete implementation-study workflow"
```

---

### Task 9: Exercise the Pipeline Against a Small Fixture Repository

**Files:**
- Create temporarily, then delete: `/tmp/implementation-study-acceptance/**`
- Modify only if a defect is found: files owned by the failing subsystem and its tests.

**Interfaces:**
- Consumes: all skill docs and scripts.
- Produces: end-to-end evidence that entry/output resolution, ledger checks, rendering, PDF checks, and integrity checks interoperate. No committed fixture artifact.

- [ ] **Step 1: Create a tiny git repository with an algorithm, tests, caller, and docs directory**

Create `/tmp/implementation-study-acceptance` containing `algo.py` with a deque-based breadth-first search, `test_algo.py`, `api.py` calling it, and `docs/.gitkeep`; initialize and commit it. Use the container's Python/git through `./shell.sh` for commands.

- [ ] **Step 2: Run the skill methodology manually on `algo.py:bfs` without experiments**

Create only these untracked files under the fixture's `docs/`: `bfs_study.md`, `bfs_study.notes.md`, and later `bfs_study.pdf`. Include at least one file citation with anchor, one derivation, one complete deque-vs-list decision block, one improvement, and inline `[C1]` references. Do not create or modify anything elsewhere in the fixture repo.

- [ ] **Step 3: Render and verify through the container wrapper**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 /workspace/skills/skills/implementation-study/make_pdf.py /tmp/implementation-study-acceptance/docs/bfs_study.md
./shell.sh python3 /workspace/skills/skills/implementation-study/check_pdf.py /tmp/implementation-study-acceptance/docs/bfs_study.pdf /tmp/implementation-study-acceptance/docs/bfs_study.md
./shell.sh python3 /workspace/skills/skills/implementation-study/check_evidence.py verify /tmp/implementation-study-acceptance/docs/bfs_study.md /tmp/implementation-study-acceptance/docs/bfs_study.notes.md --repo-root /tmp/implementation-study-acceptance --output-dir /tmp/implementation-study-acceptance/docs
```

Expected: both checkers print `clean:` and return 0; git status contains only `?? docs/...` entries.

- [ ] **Step 4: Correct any surfaced defect with a regression test**

If acceptance fails, first add a failing focused pytest reproducer to the owning test file, then make the smallest production or prose correction and rerun that focused test plus the three acceptance commands. Do not weaken a check merely to accept the fixture.

- [ ] **Step 5: Delete the temporary fixture and commit only real fixes**

Remove `/tmp/implementation-study-acceptance`. If no defect was found, make no commit. If a defect was fixed, commit the test and fix with a message naming the behavior.

---

### Task 10: Document the Third Bundle and Run Final Validation

**Files:**
- Modify: `README.md:1-165`

**Interfaces:**
- Consumes: finished skill, exact bundle name, dependencies, invocation, safety model, and manifest.
- Produces: user-facing installation and usage documentation synchronized with all three marketplace bundles.

- [ ] **Step 1: Update the opening inventory from two bundles to three**

Change the opening sentence to `Three independent plugin bundles, installed separately.` Add this table row:

```markdown
| [`implementation-study`](#implementation-study) | `implementation-study` | Turn one algorithm implementation into an evidence-grounded, verified PDF study |
```

- [ ] **Step 2: Add the new bundle section before Update**

Add `## implementation-study` with:

- `/implementation-study path/to/file.py:symbol` invocation.
- The five-phase workflow and outputs.
- The cite/derive/measure/omit rule, decision blocks, Improvements chapter, and no-modification safety rule.
- Experiment approval and the warning that experiments execute repository code without adding a sandbox.
- Install commands using `implementation-study@jgong5`.
- Requirements: Python 3 plus `websockets`, pandoc, Chrome/Chromium, and Poppler tools.
- A statement that it is user-invoked only and language-agnostic, but stops for generated, vendored, or minified input.

Use the same heading and shell/Claude-Code install layout as the existing two bundle sections.

- [ ] **Step 3: Update shared lifecycle and layout text**

In Update, list `pr-review-kit`, `amd-gpu`, or `implementation-study`. In Uninstall, replace `drops both bundles` with `drops all bundles`. In Layout, add:

```text
  implementation-study/   # SKILL.md + five phase docs, experiments.md,
                          # make_pdf.py, check_pdf.py, check_evidence.py,
                          # tutorial.css
tests/
  asm_tutorial/           # pytest suite for asm-tutorial's scripts
  implementation_study/   # pytest suite for implementation-study scripts/docs
```

- [ ] **Step 4: Run the entire test suite**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh python3 -m pytest /workspace/skills/tests -q
```

Expected: all existing and new tests pass. Record the exact pass count. If Chrome is missing, install it with the documented script and rerun; do not omit the renderer test.

- [ ] **Step 5: Run manifest validation and inventory checks**

From `/md1/users/jgong5/skills` on the host:

```bash
claude plugin validate .
claude plugin details pr-review-kit
claude plugin details amd-gpu
claude plugin details implementation-study
```

Expected: validation succeeds; skill counts are 3, 1, and 1 respectively.

- [ ] **Step 6: Review the final diff and ensure scope/ASCII discipline**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills status --short
./shell.sh git -C /workspace/skills diff --check
./shell.sh git -C /workspace/skills diff --stat main...HEAD
```

Expected: no whitespace errors; no changes under `skills/asm-tutorial/` or `tests/asm_tutorial/`; the pre-existing untracked `CLAUDE.md` remains uncommitted.

- [ ] **Step 7: Commit documentation**

```bash
cd /md1/users/jgong5/gpu_docker
./shell.sh git -C /workspace/skills add README.md
./shell.sh git -C /workspace/skills commit -m "Document implementation-study bundle"
```

- [ ] **Step 8: Perform completion verification**

Invoke `superpowers:verification-before-completion`. Re-run any command it requires and report exact outcomes rather than saying the feature is complete from memory.
