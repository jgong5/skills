"""land.py against real git repositories, with gh replaced by a recording fake."""

import json
import subprocess
import sys

import pytest

import land
import pr_state

OVERLAY = """---
repo: me/proj
integration_branch: dev
remote: origin
gate_task: true
design_entry: README.md
---
"""


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


def commit(cwd, name, text, msg=None):
    (cwd / name).write_text(text)
    git(cwd, "add", name)
    git(cwd, "commit", "-qm", msg or f"{name}={text}")
    return git(cwd, "rev-parse", "HEAD")


class Repo:
    """A bare 'GitHub' remote and a clone; `pr` publishes a head as refs/pull/7/head."""

    def __init__(self, tmp_path):
        self.remote, self.work = tmp_path / "remote.git", tmp_path / "work"
        git(tmp_path, "init", "-q", "--bare", "-b", "dev", str(self.remote))
        git(tmp_path, "clone", "-q", str(self.remote), str(self.work))
        git(self.work, "checkout", "-q", "-b", "dev")
        self.base = commit(self.work, "f", "a")
        git(self.work, "push", "-q", "origin", "dev")
        (self.work / ".claude").mkdir()
        (self.work / ".claude" / "agent-team.md").write_text(OVERLAY)
        (self.work / "msg").write_text("What the task did.\n")

    def pr(self, head):
        git(self.work, "push", "-q", "-f", "origin", f"{head}:refs/pull/7/head")

    def land_on_tip(self, *changes):
        """Move the remote's dev past the PR's base, as if other PRs landed."""
        git(self.work, "checkout", "-q", "-B", "tip", "origin/dev")
        for name, text in changes:
            sha = commit(self.work, name, text, f"landed {name}={text}")
        git(self.work, "push", "-q", "origin", "tip:dev")
        return sha


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = Repo(tmp_path)
    monkeypatch.chdir(r.work)
    monkeypatch.setattr(land.time, "sleep", lambda s: None)
    return r


@pytest.fixture
def fake_gh(monkeypatch):
    class Fake:
        holds, base, polls, calls = [], "dev", ["pending", "merged"], []
        head = None

        def __call__(self, args, check=True):
            self.calls.append(args)
            if args[:2] == ["pr", "view"]:
                return json.dumps({"title": "Add the thing"})
            if args[:3] == ["api", "-X", "PUT"]:
                return json.dumps({"status": "pending", "details": {"uuid": "u-1"}})
            if args[0] == "api" and args[1].endswith("/merge-async/u-1"):
                return json.dumps({"status": self.polls.pop(0)})
            raise AssertionError(args)

        def puts(self):
            return [c for c in self.calls if c[:3] == ["api", "-X", "PUT"]]

    fake = Fake()
    monkeypatch.setattr(pr_state, "gh", fake)
    monkeypatch.setattr(pr_state, "state", lambda n, repo=None: {
        "holds": fake.holds, "base": fake.base, "head": fake.head})
    return fake


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["land.py", "7", "--message-file", "msg", *args])
    with pytest.raises(SystemExit) as e:
        land.main()
    return e.value.code


def branch_with(repo, *changes, start=None):
    git(repo.work, "checkout", "-q", "-B", "task", start or repo.base)
    for name, text in changes:
        head = commit(repo.work, name, text)
    repo.pr(head)
    return head


def test_a_clean_land_squashes_the_reviewed_sha_with_a_numbered_title(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    assert run(monkeypatch) == 0
    (put,) = fake_gh.puts()
    assert f"sha={fake_gh.head}" in put and "merge_method=squash" in put
    assert "merge_action=direct_merge" in put and "commit_message=@msg" in put
    assert "commit_title=Add the thing (#7)" in put
    assert fake_gh.polls == []


def test_a_moved_tip_that_changes_the_tree_is_refused(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    repo.land_on_tip(("h", "other"))
    assert run(monkeypatch) == 4
    assert fake_gh.puts() == []


def test_a_moved_tip_that_conflicts_is_refused(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("f", "mine"))
    repo.land_on_tip(("f", "theirs"))
    assert run(monkeypatch) == 4
    assert fake_gh.puts() == []


def test_a_stacked_child_needs_its_parents_reviewed_head_as_merge_base(repo, fake_gh, monkeypatch):
    parent = branch_with(repo, ("f", "b"))
    fake_gh.head = branch_with(repo, ("f", "c"), start=parent)
    repo.land_on_tip(("f", "b"))  # the parent, landed squashed: same tree, new commit
    assert run(monkeypatch) == 4  # the false conflict the plain form reports
    assert run(monkeypatch, "--merge-base", parent) == 0
    assert "commit_title=Add the thing (#7)" in fake_gh.puts()[0]


def test_a_gated_batch_tree_lands_where_the_reviewed_tree_would_not(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    tip = repo.land_on_tip(("h", "other"))  # the batch's PR below, already landed
    git(repo.work, "checkout", "-q", "--detach", tip)
    git(repo.work, "merge", "-q", "--no-edit", fake_gh.head)
    batch_tree = git(repo.work, "rev-parse", "HEAD^{tree}")
    assert run(monkeypatch, "--expect-tree", fake_gh.head + "^{tree}") == 4
    assert run(monkeypatch, "--expect-tree", batch_tree) == 0


def test_a_hold_or_a_foreign_base_stops_before_any_git_or_merge(repo, fake_gh, monkeypatch):
    fake_gh.holds = ["need human on the PR"]
    assert run(monkeypatch) == 3
    fake_gh.holds, fake_gh.base = [], "task-3"
    assert run(monkeypatch) == 3
    assert fake_gh.calls == []


def test_a_failed_merge_exits_nonzero(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    fake_gh.polls = ["pending", "failed"]
    assert run(monkeypatch) == 5


def test_a_poll_gh_fails_on_is_retried_after_github_accepted_the_merge(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    failures = [True]

    def flaky(args, check=True):
        if args[1].endswith("/merge-async/u-1") and failures:
            failures.pop()
            if check:
                raise SystemExit("gh api failed: HTTP 502")
            return ""
        return fake_gh(args, check)

    monkeypatch.setattr(pr_state, "gh", flaky)
    assert run(monkeypatch) == 0
    assert fake_gh.polls == []


def test_the_overlay_path_is_not_an_option(repo, fake_gh, monkeypatch, capsys):
    fake_gh.head = branch_with(repo, ("g", "new"))
    assert run(monkeypatch, "--overlay", ".claude/agent-team.md") == 2
    assert "unrecognized arguments: --overlay" in capsys.readouterr().err
    assert fake_gh.puts() == []
