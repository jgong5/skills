"""line_count.py against real temporary git repositories."""

import subprocess
import sys

import line_count

OVERLAY = """---
repo: me/proj
integration_branch: main
remote: origin
gate_task: true
design_entry: README.md
{extra}---
"""


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


def repo(tmp_path, files, extra=""):
    """A repository whose first commit holds `files` and the overlay; returns its path and sha."""
    git(tmp_path, "init", "-q")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "agent-team.md").write_text(OVERLAY.format(extra=extra))
    return tmp_path, change(tmp_path, files)


def change(cwd, files):
    """Write (text or bytes) or, for None, delete each file; commit; return the sha."""
    for name, content in files.items():
        p = cwd / name
        if content is None:
            p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content) if isinstance(content, bytes) else p.write_text(content)
    git(cwd, "add", "-A")
    git(cwd, "commit", "-qm", "c")
    return git(cwd, "rev-parse", "HEAD")


def rows(cwd, base, *head):
    out = subprocess.run([sys.executable, line_count.__file__, base, *head], cwd=cwd,
                         check=True, capture_output=True, text=True).stdout
    return [line.split("\t") for line in out.splitlines()]


def lines(stem, n, indent=""):
    return "".join(f"{indent}{stem}_{i} = compute_something({i}) + another_term\n" for i in range(n))


def test_named_result_moved_block_under_a_class_and_deletions(tmp_path):
    cwd, base = repo(tmp_path, {"a.py": "header = 1\n" + lines("value", 40) + lines("gone", 20)})
    change(cwd, {"a.py": "header = 1\n", "b.py": "class K:\n" + lines("value", 40, "    ")})
    assert rows(cwd, base) == [["a.py", "code", "0", "0", "20", "5"],
                               ["b.py", "code", "1", "40", "0", "11"],
                               ["total", "code", "1", "40", "20", "16"],
                               ["total", "test", "0", "0", "0", "0"]]


def test_pure_deletion_counts_a_quarter_and_total_rounds_up(tmp_path):
    cwd, base = repo(tmp_path, {"a.py": lines("v", 5)})
    change(cwd, {"a.py": lines("v", 2)})
    assert rows(cwd, base)[0] == ["a.py", "code", "0", "0", "3", "0.75"]
    assert rows(cwd, base)[1] == ["total", "code", "0", "0", "3", "1"]


def test_short_line_moved_counts_as_deleted_plus_added(tmp_path, monkeypatch):
    cwd, base = repo(tmp_path, {"a.py": "x = 1\n" + lines("keep", 3)})
    change(cwd, {"a.py": lines("keep", 3), "b.py": "x = 1\n"})
    monkeypatch.chdir(cwd)
    assert line_count.count(base, "HEAD", []) == [("a.py", "code", 0, 0, 1), ("b.py", "code", 1, 0, 0)]


def test_pure_rename_and_binary_file_count_nothing(tmp_path, monkeypatch):
    cwd, base = repo(tmp_path, {"old.py": lines("v", 10)})
    change(cwd, {"old.py": None, "new.py": lines("v", 10), "blob.bin": bytes(range(256)) * 8})
    monkeypatch.chdir(cwd)
    assert sorted(line_count.count(base, "HEAD", [])) == [("blob.bin", "code", 0, 0, 0),
                                                         ("new.py", "code", 0, 0, 0)]


DEFAULT_TESTS = ["tests/a.py", "x/test/b.py", "web/__tests__/c.js", "test_d.py", "e_test.go",
                 "f.test.ts", "g.spec.js"]
DEFAULT_CODE = ["src/contest.py", "testing/h.py", "latest.py"]


def test_test_files_unset_uses_the_default_and_the_overlay_still_loads(tmp_path):
    cwd, base = repo(tmp_path, {"README.md": "r\n"})
    change(cwd, {p: "x\n" for p in DEFAULT_TESTS + DEFAULT_CODE})
    classes = {r[0]: r[1] for r in rows(cwd, base) if r[0] != "total"}
    assert classes == {**{p: "test" for p in DEFAULT_TESTS}, **{p: "code" for p in DEFAULT_CODE}}


def test_test_files_set_replaces_the_default(tmp_path):
    cwd, base = repo(tmp_path, {"README.md": "r\n"}, "test_files: checks/*.py, *.golden\n")
    change(cwd, {"checks/deep/a.py": "x\n", "out.golden": "x\n", "tests/test_b.py": "x\n"})
    classes = {r[0]: r[1] for r in rows(cwd, base, "HEAD") if r[0] != "total"}
    assert classes == {"checks/deep/a.py": "test", "out.golden": "test", "tests/test_b.py": "code"}
