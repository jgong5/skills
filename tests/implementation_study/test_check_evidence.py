import json
import os
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


def _committed_repo(tmp_path, name="repo"):
    """A git repository with one committed file and an empty output directory."""
    repo = tmp_path / name
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "algo.py").write_text("one\n")
    _git(repo, "add", "algo.py")
    _git(repo, "commit", "-m", "base")
    out = repo / "docs"
    out.mkdir()
    return repo, out


def test_git_integrity_accepts_an_output_path_containing_an_arrow(tmp_path):
    repo, out = _committed_repo(tmp_path)
    (out / "a -> b.txt").write_text("study\n")
    assert check_git_integrity(repo, out) == []


def test_git_integrity_rejects_an_outside_path_containing_an_arrow(tmp_path):
    repo, out = _committed_repo(tmp_path)
    (repo / "evil -> docs").write_text("x\n")
    assert "outside output directory" in " ".join(check_git_integrity(repo, out))


def test_git_integrity_accepts_a_backslash_in_an_output_path(tmp_path):
    repo, out = _committed_repo(tmp_path)
    (out / "back\\slash.md").write_text("study\n")
    assert check_git_integrity(repo, out) == []


def test_git_integrity_reports_a_rename_exactly_once(tmp_path):
    repo, out = _committed_repo(tmp_path)
    _git(repo, "mv", "algo.py", "renamed.py")
    problems = check_git_integrity(repo, out)
    assert len(problems) == 1
    assert "tracked change" in problems[0]


def test_git_integrity_rejects_an_untracked_symlink_pointing_into_output(tmp_path):
    repo, out = _committed_repo(tmp_path)
    (repo / "sneak").symlink_to(out, target_is_directory=True)
    assert "outside output directory" in " ".join(check_git_integrity(repo, out))


def test_git_integrity_resolves_status_paths_against_the_git_toplevel(tmp_path):
    repo, _ = _committed_repo(tmp_path)
    sub = repo / "sub"
    out = sub / "docs"
    out.mkdir(parents=True)
    (out / "algo_study.md").write_text("study\n")
    assert check_git_integrity(sub, out) == []


def test_git_integrity_rejects_an_output_directory_that_is_the_root(tmp_path):
    repo, _ = _committed_repo(tmp_path)
    assert "output directory" in " ".join(check_git_integrity(repo, repo))


def test_continuation_lines_do_not_fold_across_a_blank_line():
    entries = parse_ledger(
        "- [C1] One. cite: a.py:1 `x`\n"
        "\n"
        "  loose indented prose\n"
    )
    assert entries["C1"].source == "a.py:1 `x`"


def test_indented_continuation_still_joins_to_its_entry():
    entries = parse_ledger("- [C1] One. cite: a.py:1\n  `x`\n")
    assert entries["C1"].source == "a.py:1 `x`"


def test_citation_cannot_escape_the_repository_through_a_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("classified\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "link").symlink_to(outside, target_is_directory=True)
    entries = parse_ledger("- [C1] Claim. cite: link/secret.txt:1 `classified`\n")
    assert "escapes" in check_citations(entries, repo)[0]


def test_parse_ledger_rejects_an_id_no_derivation_could_reference():
    with pytest.raises(EvidenceFormatError, match="PERF"):
        parse_ledger("- [PERF] One. cite: a.py:1 `x`\n")


def test_snapshot_rejects_an_output_directory_that_is_the_root(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "algo.py").write_text("one\n")
    snapshot = tmp_path / "x.integrity.json"
    with pytest.raises(ValueError, match="output directory"):
        write_integrity_snapshot(repo, repo, snapshot, [])
    assert not snapshot.exists()
    assert "output directory" in " ".join(
        check_snapshot_integrity(repo, repo, snapshot)
    )


def test_url_citation_with_a_port_is_not_a_file_citation(tmp_path):
    entries = parse_ledger(
        "- [C1] Claim. cite: https://example.com:8080 `the spec`\n"
    )
    assert check_citations(entries, tmp_path) == []


def test_prose_refs_stay_hidden_across_a_mixed_fence_marker():
    entries = parse_ledger("- [C1] One. cite: a.py:1 `one`\n")
    prose = "```text\n~~~\n[C9]\n```\nReal [C1].\n"
    assert check_prose_coverage(prose, entries) == []


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


# --- the non-git metadata walk ------------------------------------------------
#
# The snapshot has two independent halves: sha256 hashes for the handful of
# files the ledger cites, and size/mtime metadata for every other file outside
# the output directory. Only the hashes were pinned before, so deleting the
# metadata walk entirely -- the half that catches an addition, a deletion, or
# an edit to a file nobody cited -- broke nothing. These four tests fail if it
# goes away.

def _snapshot_repo(tmp_path):
    """A non-git repo with one cited file, one uncited file, and an output dir."""
    repo = tmp_path / "repo"
    out = repo / "docs"
    out.mkdir(parents=True)
    (repo / "algo.py").write_text("one\n")
    (repo / "README").write_text("read\n")
    snapshot = out / "algo_study.integrity.json"
    write_integrity_snapshot(repo, out, snapshot, [Path("algo.py")])
    return repo, out, snapshot


def test_snapshot_records_metadata_for_files_the_ledger_never_cites(tmp_path):
    repo, out, snapshot = _snapshot_repo(tmp_path)
    data = json.loads(snapshot.read_text())
    assert sorted(data["hashes"]) == ["algo.py"]
    # README is not cited, so it is not hashed -- but it must still be tracked
    # by size and mtime, or nothing would notice it changing.
    assert sorted(data["files"]) == ["README", "algo.py"]
    assert set(data["files"]["README"]) == {"size", "mtime_ns"}
    assert data["files"]["README"]["size"] == len("read\n")


def test_snapshot_detects_a_file_added_outside_the_output_directory(tmp_path):
    repo, out, snapshot = _snapshot_repo(tmp_path)
    (repo / "scratch.txt").write_text("new\n")
    problems = check_snapshot_integrity(repo, out, snapshot)
    assert problems == ["added file outside output directory: scratch.txt"]


def test_snapshot_detects_a_deleted_file(tmp_path):
    repo, out, snapshot = _snapshot_repo(tmp_path)
    (repo / "README").unlink()
    assert check_snapshot_integrity(repo, out, snapshot) == ["deleted file: README"]


def test_snapshot_detects_a_size_change_in_an_uncited_file(tmp_path):
    repo, out, snapshot = _snapshot_repo(tmp_path)
    (repo / "README").write_text("read some more\n")
    problems = check_snapshot_integrity(repo, out, snapshot)
    assert len(problems) == 1
    assert problems[0].startswith("README: size changed")


def test_snapshot_detects_an_mtime_change_with_identical_bytes(tmp_path):
    # A formatter that rewrites a file byte-for-byte, or a build step that
    # re-links without regenerating, changes neither size nor content. mtime
    # is the only signal left, and analysis.md/verification.md both promise
    # this is reported rather than tolerated.
    repo, out, snapshot = _snapshot_repo(tmp_path)
    stat = (repo / "README").stat()
    os.utime(repo / "README",
             ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert check_snapshot_integrity(repo, out, snapshot) == ["README: mtime changed"]


# --- derivations must show their work -----------------------------------------

@pytest.mark.parametrize("source", [
    "C1",           # no separator at all
    "C1 --",        # separator, nothing after it
    "C1 --   ",     # separator and whitespace only
])
def test_derivation_without_reasoning_is_rejected(source):
    entries = parse_ledger(
        "- [C1] One. cite: a.py:1 `x`\n"
        f"- [C2] Two. derive: {source}\n"
    )
    problems = check_derivations(entries)
    assert problems == ["C2: derivation has no reasoning after '--'"]


def test_derivation_with_reasoning_is_accepted():
    entries = parse_ledger(
        "- [C1] One. cite: a.py:1 `x`\n"
        "- [C2] Two. derive: C1 -- one implies two because the queue is FIFO\n"
    )
    assert check_derivations(entries) == []


# --- measurement artifacts ----------------------------------------------------

def _measured(tmp_path, *, omit=()):
    """An experiments directory with every required artifact except `omit`."""
    exp = tmp_path / "bfs_study_experiments"
    exp.mkdir()
    files = {
        "bench.py": "print('ok')\n",
        "bench.out": "ok\n",
        "ENV.md": "OS: test\n",
        "PLAN.md": "- [x] [C3] bench.py -- compare deque and list; under 10s\n",
    }
    for name, text in files.items():
        if name not in omit:
            (exp / name).write_text(text)
    entries = parse_ledger(
        "- [C3] Deque wins. measure: "
        "bfs_study_experiments/bench.py -> bfs_study_experiments/bench.out\n"
    )
    return entries


def test_measurement_without_env_md_is_rejected(tmp_path):
    entries = _measured(tmp_path, omit=("ENV.md",))
    problems = check_measurements(entries, tmp_path)
    assert problems == ["C3: bfs_study_experiments/ has no ENV.md"]


def test_measurement_without_plan_md_is_rejected(tmp_path):
    entries = _measured(tmp_path, omit=("PLAN.md",))
    problems = check_measurements(entries, tmp_path)
    assert problems == ["C3: bfs_study_experiments/ has no PLAN.md"]


# --- path escapes -------------------------------------------------------------
#
# _resolve_under closes three escapes; the symlink one is covered above, and
# these cover the two lexical ones, on both sides (citations resolve under the
# repository root, measurements under the output directory).

@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd"])
def test_citation_cannot_escape_the_repository_lexically(tmp_path, path):
    entries = parse_ledger(f"- [C1] Claim. cite: {path}:1 `classified`\n")
    problems = check_citations(entries, tmp_path)
    assert len(problems) == 1
    assert "escapes the root" in problems[0] or "absolute path" in problems[0]


@pytest.mark.parametrize("path", ["../bench.py", "/tmp/bench.py"])
def test_measurement_cannot_escape_the_output_directory_lexically(tmp_path, path):
    entries = parse_ledger(
        f"- [C3] Deque wins. measure: {path} -> bfs_study_experiments/bench.out\n"
    )
    problems = check_measurements(entries, tmp_path)
    assert len(problems) == 1
    assert "escapes the root" in problems[0] or "absolute path" in problems[0]


# --- verify's git path, end to end --------------------------------------------

def _git_study(tmp_path):
    """A committed git repo whose docs/ holds a study, its notes, and nothing else."""
    repo, out = _committed_repo(tmp_path)
    (repo / "algo.py").write_text("queue = [source]\n")
    _git(repo, "commit", "-am", "source")
    (out / "algo_study.md").write_text("The queue begins with the source [C1].\n")
    (out / "algo_study.notes.md").write_text(
        "## Ledger\n\n- [C1] The queue begins with the source. "
        "cite: algo.py:1 `queue = [source]`\n"
    )
    return repo, out, out / "algo_study.md", out / "algo_study.notes.md"


def test_main_verify_in_a_git_repo_is_clean_without_a_snapshot(tmp_path, capsys):
    repo, out, study, notes = _git_study(tmp_path)
    assert main(["verify", str(study), str(notes), "--repo-root", str(repo),
                 "--output-dir", str(out)]) == 0
    assert "clean: 1 ledger entries verified" in capsys.readouterr().out


def test_main_verify_in_a_git_repo_reports_a_littered_file(tmp_path, capsys):
    repo, out, study, notes = _git_study(tmp_path)
    (repo / "scratch.txt").write_text("littered\n")
    assert main(["verify", str(study), str(notes), "--repo-root", str(repo),
                 "--output-dir", str(out)]) == 1
    errors = capsys.readouterr().err
    assert "PROBLEM: untracked file outside output directory: scratch.txt" in errors
