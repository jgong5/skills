"""land.py against real git repositories, with gh replaced by a recording fake."""

import json
import subprocess
import sys

import pytest

import land
import pr_state

REAL_STATE = pr_state.state

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
    monkeypatch.setattr(pr_state, "state", lambda n, repo=None, equivalent=None: {
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


def test_a_stacked_child_is_checked_by_the_merge_github_does_not_a_merge_base(
        repo, fake_gh, monkeypatch):
    parent = branch_with(repo, ("f", "b"))
    fake_gh.head = branch_with(repo, ("f", "c"), start=parent)
    repo.land_on_tip(("f", "b"))  # the parent, landed squashed: same tree, new commit
    assert run(monkeypatch) == 4  # GitHub's merge conflicts, and ignores any merge base
    assert run(monkeypatch, "--merge-base", parent) == 4
    assert fake_gh.puts() == []


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


def test_a_rebased_child_lands_on_its_old_approval_only_if_its_content_is_unchanged(
        repo, fake_gh, monkeypatch):
    parent = branch_with(repo, ("f", "b"))
    approved = branch_with(repo, ("g", "c"), start=parent)
    batch_tree = approved + "^{tree}"  # the tip was the batch's base: merging is a fast-forward
    tip = repo.land_on_tip(("f", "b"))  # the parent, landed squashed
    pr = {"number": 7, "state": "OPEN", "body": "", "baseRefName": "dev", "labels": [],
          "reviews": [], "closingIssuesReferences": [], "title": "Add the thing",
          "comments": [{"createdAt": "2026-01-02T00:00:00Z", "author": {"login": "rev"},
                        "body": f"APPROVE @ {approved[:7]}."}]}
    monkeypatch.setattr(pr_state, "state", REAL_STATE)
    monkeypatch.setattr(pr_state, "gh", lambda args, check=True: json.dumps(pr) if args[:2] == [
        "pr", "view"] else fake_gh(args, check))
    land_args = ("--expect-tree", batch_tree, "--merge-base", parent)

    # GitHub rebased the linked child onto the squash commit: new head, new content.
    pr["headRefOid"] = branch_with(repo, ("g", "c"), ("h", "x"), start=tip)
    pr["commits"] = [{"committedDate": "2026-01-03T00:00:00Z", "oid": pr["headRefOid"]}]
    assert run(monkeypatch, *land_args) == 3
    # Nor does a gated tree that is the changed head's own: the approved sha must land as it too.
    assert run(monkeypatch, "--expect-tree", pr["headRefOid"] + "^{tree}", "--merge-base", parent) == 3
    assert fake_gh.puts() == []

    # The same rebase with the content unchanged lands, at the head it checked.
    pr["headRefOid"] = branch_with(repo, ("g", "c"), start=tip)
    pr["commits"] = [{"committedDate": "2026-01-03T00:00:00Z", "oid": pr["headRefOid"]}]
    assert run(monkeypatch, *land_args) == 0
    assert f"sha={pr['headRefOid']}" in fake_gh.puts()[0]


@pytest.mark.parametrize("labels, merged", [(["land as merge"], True), ([], False)])
def test_a_pr_labeled_land_as_merge_lands_as_a_merge_whose_second_parent_is_its_head(
        repo, fake_gh, monkeypatch, labels, merged):
    fake_gh.head = branch_with(repo, ("g", "new"))

    def github(args, check=True):
        """The PR carries `labels`; a PUT lands the sha the way its merge_method asks."""
        if args[:2] == ["pr", "view"]:
            return json.dumps({"title": "Add the thing", "labels": [{"name": n} for n in labels]})
        if args[:3] != ["api", "-X", "PUT"]:
            return fake_gh(args, check)
        sha = next(a[4:] for a in args if a.startswith("sha="))
        git(repo.work, "checkout", "-q", "-B", "landed", "origin/dev")
        if "merge_method=merge" in args:
            git(repo.work, "merge", "-q", "--no-ff", "-m", "landed", sha)
        else:
            assert "merge_method=squash" in args
            git(repo.work, "merge", "-q", "--squash", sha)
            git(repo.work, "commit", "-qm", "landed")
        git(repo.work, "push", "-q", "origin", "landed:dev")
        return json.dumps({"status": "merged"})

    monkeypatch.setattr(pr_state, "gh", github)
    assert run(monkeypatch) == 0
    parents = git(repo.work, "log", "-1", "--format=%P", "origin/dev").split()
    assert parents == ([repo.base, fake_gh.head] if merged else [repo.base])
    assert git(repo.work, "rev-parse", "origin/dev^{tree}") == git(
        repo.work, "rev-parse", fake_gh.head + "^{tree}")


def test_a_rebased_child_cut_before_its_parents_last_round_lands_given_the_parents_head(
        repo, fake_gh, monkeypatch):
    round1 = branch_with(repo, ("g", "1"))
    parent = branch_with(repo, ("g", "2"), start=round1)
    approved = branch_with(repo, ("h", "1"), start=round1)
    tip = repo.land_on_tip(("g", "2"))  # the parent's last round, landed squashed
    pr = {"number": 7, "state": "OPEN", "body": "", "baseRefName": "dev", "labels": [],
          "reviews": [], "closingIssuesReferences": [], "title": "Add the thing",
          "comments": [{"createdAt": "2026-01-02T00:00:00Z", "author": {"login": "rev"},
                        "body": f"APPROVE @ {approved[:7]}."}]}
    pr["headRefOid"] = branch_with(repo, ("h", "1"), start=tip)  # GitHub's rebase
    pr["commits"] = [{"committedDate": "2026-01-03T00:00:00Z", "oid": pr["headRefOid"]}]
    monkeypatch.setattr(pr_state, "state", REAL_STATE)
    monkeypatch.setattr(pr_state, "gh", lambda args, check=True: json.dumps(pr) if args[:2] == [
        "pr", "view"] else fake_gh(args, check))
    # Based on the parent's head itself, the approved sha would undo the parent's last round.
    assert run(monkeypatch, "--expect-tree", pr["headRefOid"] + "^{tree}", "--merge-base", parent) == 0
    assert f"sha={pr['headRefOid']}" in fake_gh.puts()[0]


def test_a_base_update_lands_on_its_parents_approval_only_with_the_gated_tree(
        repo, fake_gh, monkeypatch):
    approved = branch_with(repo, ("g", "1"), ("h", "1"))
    tip = repo.land_on_tip(("g", "2"))  # GitHub's merge of `approved` conflicts
    gated = branch_with(repo, ("h", "1"), start=tip)  # the batch resolved it: g=2, h=1
    pr = {"number": 7, "state": "OPEN", "body": "", "baseRefName": "dev", "labels": [],
          "reviews": [], "closingIssuesReferences": [], "title": "Add the thing",
          "comments": [{"createdAt": "2026-01-02T00:00:00Z", "author": {"login": "rev"},
                        "body": f"APPROVE @ {approved[:7]}."}]}
    monkeypatch.setattr(pr_state, "state", REAL_STATE)
    monkeypatch.setattr(pr_state, "gh", lambda args, check=True: json.dumps(pr) if args[:2] == [
        "pr", "view"] else fake_gh(args, check))

    def push(tree, *parents):
        head = git(repo.work, "commit-tree", tree, *[a for p in parents for a in ("-p", p)],
                   "-m", "Merge dev")
        repo.pr(head)
        pr["headRefOid"] = head
        pr["commits"] = [{"committedDate": "2026-01-03T00:00:00Z", "oid": head}]

    push(gated + "^{tree}", tip, approved)  # parents the wrong way round
    assert run(monkeypatch, "--expect-tree", gated + "^{tree}") == 3
    push(approved + "^{tree}", approved, tip)  # a tree other than the gated one
    assert run(monkeypatch, "--expect-tree", gated + "^{tree}") == 3
    assert fake_gh.puts() == []
    push(gated + "^{tree}", approved, tip)
    assert run(monkeypatch, "--expect-tree", gated + "^{tree}") == 0
    assert f"sha={pr['headRefOid']}" in fake_gh.puts()[0]


def test_a_fetch_after_the_tip_fetch_does_not_change_the_tip(repo, fake_gh, monkeypatch):
    fake_gh.head = branch_with(repo, ("g", "new"))
    git(repo.work, "checkout", "-q", "-B", "other", repo.base)
    other = commit(repo.work, "h", "other")
    git(repo.work, "push", "-q", "origin", "other")
    real = land.git

    def git_then_fetch_other(*args):
        """Another command in the same worktree fetches right after each of land.py's fetches."""
        out = real(*args)
        if args[0] == "fetch":
            real("fetch", "-q", "origin", "refs/heads/other")
        return out

    monkeypatch.setattr(land, "git", git_then_fetch_other)
    assert land.fetch_tip("origin", "dev", 7) == repo.base
    assert real("rev-parse", "FETCH_HEAD")[1] == other
    assert run(monkeypatch) == 0
