import subprocess
from pathlib import Path

import overlay

GOOD = """---
repo: me/proj
integration_branch: dev
# a comment
gate_task: pytest -q && ruff check .
design_entry: docs/design.md
max_tasks: 3
---
Project rules: run as the container user.
"""


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def repo_with(tmp_path, monkeypatch, text, remotes=(("fork", "git@github.com:me/proj.git"),)):
    main = tmp_path / "proj"
    main.mkdir()
    git(main, "init", "-q")
    for name, url in remotes:
        git(main, "remote", "add", name, url)
    (main / ".claude").mkdir()
    (main / ".claude" / "agent-team.md").write_text(text)
    monkeypatch.chdir(main)
    return main


def test_parse_splits_keys_from_body():
    keys, body, problems = overlay.parse(GOOD)
    assert problems == []
    assert keys["gate_task"] == "pytest -q && ruff check ."
    assert body.startswith("Project rules")


def test_parse_reports_typos_and_shape():
    _, _, problems = overlay.parse("---\nrepo: a/b\ngate_tsk: x\nremote\n---\n")
    assert any("unknown key 'gate_tsk'" in p for p in problems)
    assert any("not `key: value`" in p for p in problems)
    assert overlay.parse("repo: a/b\n")[2] == ["no frontmatter: the file must open with a --- block"]


def test_remotes_for_matches_https_and_ssh_forms_only_for_that_repo():
    remote_v = "\n".join([
        "origin\thttps://github.com/Upstream/Proj (fetch)",
        "origin\thttps://github.com/Upstream/Proj (push)",
        "fork\tgit@github.com:me/proj.git (fetch)",
        "mirror\thttps://github.com/me/proj/ (fetch)",
        "other\thttps://github.com/me/project (fetch)",
    ])
    assert overlay.remotes_for("me/proj", remote_v) == ["fork", "mirror"]
    assert overlay.remotes_for("upstream/proj", remote_v) == ["origin"]


def test_load_resolves_remote_defaults_and_worktree_root(tmp_path, monkeypatch):
    main = repo_with(tmp_path, monkeypatch, GOOD, remotes=(
        ("origin", "https://github.com/upstream/proj"), ("fork", "git@github.com:me/proj.git")))
    keys, _, problems = overlay.load()
    assert problems == []
    assert keys["remote"] == "fork"
    assert keys["max_tasks"] == "3" and keys["split_loc"] == "1000"
    assert keys["publish_language"] == "English"
    assert Path(keys["worktree_root"]) == main.parent.resolve() / "proj-worktrees"


def test_load_lists_every_problem(tmp_path, monkeypatch):
    repo_with(tmp_path, monkeypatch, "---\nrepo: me/proj\nsplit_loc: lots\n---\n",
              remotes=(("a", "https://github.com/me/proj"), ("b", "git@github.com:me/proj")))
    _, _, problems = overlay.load()
    assert "missing required key 'gate_task'" in problems
    assert any(p.startswith("split_loc must be a positive integer") for p in problems)
    assert any(p.startswith("2 remotes point at me/proj") for p in problems)


def test_the_default_path_is_found_from_a_subdirectory(tmp_path, monkeypatch):
    main = repo_with(tmp_path, monkeypatch, GOOD)
    (main / "src").mkdir()
    monkeypatch.chdir(main / "src")
    assert overlay.load()[2] == []


def test_an_explicit_remote_wins(tmp_path, monkeypatch):
    repo_with(tmp_path, monkeypatch, GOOD.replace("max_tasks: 3", "remote: origin"), remotes=())
    keys, _, problems = overlay.load()
    assert problems == [] and keys["remote"] == "origin"


def test_a_missing_file_is_a_problem_not_a_crash(tmp_path):
    assert overlay.load(str(tmp_path / "nope.md"))[2][0].startswith("cannot read")
