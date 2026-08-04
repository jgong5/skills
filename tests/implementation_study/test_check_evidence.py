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
    main,
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


def test_extending_snapshot_adds_hashes_for_new_citations(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = repo / "docs"
    out.mkdir()
    (repo / "a.py").write_text("a\n")
    (repo / "b.py").write_text("b\n")
    snapshot = out / "x.integrity.json"
    write_integrity_snapshot(repo, out, snapshot, [Path("a.py")])
    assert extend_integrity_snapshot(repo, out, snapshot, [Path("b.py")]) == []
    data = json.loads(snapshot.read_text())
    assert sorted(data["hashes"]) == ["a.py", "b.py"]
    assert check_snapshot_integrity(repo, out, snapshot) == []


def _study(tmp_path, anchor="queue = [source]"):
    """A minimal non-git study: one source file, one ledger entry, one PDF-less
    document that cites it."""
    repo = tmp_path / "repo"
    out = repo / "docs"
    out.mkdir(parents=True)
    (repo / "algo.py").write_text("queue = [source]\n")
    study = out / "algo_study.md"
    study.write_text("The queue begins with the source [C1].\n")
    notes = out / "algo_study.notes.md"
    notes.write_text(
        f"## Ledger\n\n- [C1] The queue begins with the source. "
        f"cite: algo.py:1 `{anchor}`\n"
    )
    return repo, out, study, notes


def test_main_snapshot_then_verify_is_clean(tmp_path, capsys):
    repo, out, study, notes = _study(tmp_path)
    snapshot = out / "algo_study.integrity.json"
    assert main(["snapshot", "--repo-root", str(repo), "--output-dir", str(out),
                 "--snapshot", str(snapshot), "--cited-file", "algo.py"]) == 0
    assert main(["verify", str(study), str(notes), "--repo-root", str(repo),
                 "--output-dir", str(out), "--snapshot", str(snapshot)]) == 0
    assert "clean: 1 ledger entries verified" in capsys.readouterr().out


def test_main_verify_reports_a_bad_anchor(tmp_path, capsys):
    repo, out, study, notes = _study(tmp_path, anchor="stack = [source]")
    snapshot = out / "algo_study.integrity.json"
    assert main(["snapshot", "--repo-root", str(repo), "--output-dir", str(out),
                 "--snapshot", str(snapshot), "--cited-file", "algo.py"]) == 0
    assert main(["verify", str(study), str(notes), "--repo-root", str(repo),
                 "--output-dir", str(out), "--snapshot", str(snapshot)]) == 1
    errors = capsys.readouterr().err
    assert "PROBLEM:" in errors
    assert "does not appear in algo.py" in errors


def test_main_verify_without_git_or_snapshot_is_a_problem(tmp_path, capsys):
    repo, out, study, notes = _study(tmp_path)
    assert main(["verify", str(study), str(notes), "--repo-root", str(repo),
                 "--output-dir", str(out)]) == 1
    assert "no --snapshot" in capsys.readouterr().err
