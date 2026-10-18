"""batch.py against real git repositories, with GitHub replaced by a small simulation."""

import json
import subprocess

import pytest

import batch
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


def commit(cwd, *files, merge=None):
    for name, text in files:
        (cwd / name).write_text(text)
        git(cwd, "add", name)
    if merge:
        git(cwd, "merge", "-q", "--no-edit", merge)
    else:
        git(cwd, "commit", "-qm", " ".join(f"{n}={t}" for n, t in files))
    return git(cwd, "rev-parse", "HEAD")


class GitHub:
    """A bare remote plus the PR behaviour batch.py meets: squash landing through
    merge-async, and, for a linked stack, retargeting and rebasing the child of a
    landed PR -- except a child carrying merges, which GitHub leaves alone. That
    happens a moment after the landing: the child's next view still shows it before."""

    def __init__(self, remote):
        self.remote, self.prs, self.linked, self.calls, self.late = remote, {}, set(), [], {}

    def head(self, n):
        return git(self.remote, "rev-parse", f"refs/heads/{self.prs[n]['branch']}")

    def __call__(self, args, check=True):
        self.calls.append(args)
        if args[:2] == ["pr", "view"] and int(args[2]) in self.late:
            late = self.late[int(args[2])]
            late[0] -= 1
            if late[0] < 0:
                self.rebase(*self.late.pop(int(args[2]))[1:])
        for n, p in self.prs.items():  # GitHub keeps refs/pull/N/head on the branch
            git(self.remote, "update-ref", f"refs/pull/{n}/head", self.head(n))
        if args[:2] == ["pr", "view"]:
            n = int(args[2])
            p, head = self.prs[n], self.head(n)
            return json.dumps({
                "number": n, "state": p["state"], "body": "", "title": f"Task {n}", "labels": [],
                "headRefOid": head, "headRefName": p["branch"], "baseRefName": p["base"],
                "reviews": [], "closingIssuesReferences": [], "comments": p["comments"],
                "commits": [{"committedDate": "2026-01-03T00:00:00Z", "oid": head}]})
        if args[0] == "api" and "/stacks?pull_request=" in args[1]:
            n = int(args[1].rsplit("=", 1)[1])
            return json.dumps([{"pull_requests": [{"number": m} for m in sorted(self.linked)]}]
                              if n in self.linked else [])
        if args[:3] == ["api", "-X", "PATCH"]:
            self.prs[int(args[3].rsplit("/", 1)[1])]["base"] = args[5].split("=", 1)[1]
            return "{}"
        if args[:2] == ["pr", "comment"]:
            self.prs[int(args[2])]["comments"].append(
                {"createdAt": "2026-01-04T00:00:00Z", "author": {"login": "orc"}, "body": args[-1]})
            return ""
        if args[:3] == ["api", "-X", "PUT"]:
            return json.dumps({"status": self.merge(int(args[3].split("/")[-2]), args)})
        raise AssertionError(args)

    def merge(self, n, args):
        sha, p = next(a[4:] for a in args if a.startswith("sha=")), self.prs[n]
        tip = git(self.remote, "rev-parse", "refs/heads/dev")
        if sha != self.head(n) or p["base"] != "dev":
            return "failed"
        r = subprocess.run(["git", "merge-tree", "--write-tree", tip, sha], cwd=self.remote,
                           capture_output=True, text=True)
        if r.returncode:
            return "failed"
        squash = git(self.remote, "commit-tree", r.stdout.split()[0], "-p", tip, "-m", f"#{n}")
        git(self.remote, "update-ref", "refs/heads/dev", squash)
        p["state"] = "MERGED"
        for c in self.prs.values():
            if c["state"] == "OPEN" and c["base"] == p["branch"] and c["number"] in self.linked:
                self.late[c["number"]] = [1, c, sha, squash]
        return "merged"

    def rebase(self, c, old, new):
        """Retarget the child, and replay its own commits onto `new` as GitHub's stack rebase does."""
        c["base"] = "dev"
        head = self.head(c["number"])
        if git(self.remote, "rev-list", "--merges", f"{old}..{head}"):
            return
        own = git(self.remote, "merge-base", head, old)
        tree = git(self.remote, "merge-tree", "--write-tree", "--merge-base", own, new, head)
        rebased = git(self.remote, "commit-tree", tree.split()[0], "-p", new, "-m", "rebased")
        git(self.remote, "update-ref", f"refs/heads/{c['branch']}", rebased)


@pytest.fixture
def gh(tmp_path, monkeypatch):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "dev", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(work))
    git(work, "checkout", "-q", "-b", "dev")
    (work / ".claude").mkdir()
    (work / ".claude" / "agent-team.md").write_text(OVERLAY)
    (work / "msgs").mkdir()
    for n in range(1, 5):
        (work / "msgs" / f"{n}.txt").write_text(f"Task {n}.\n")
    monkeypatch.chdir(work)
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t")
        monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@t")
    monkeypatch.setattr(batch.time, "sleep", lambda s: None)
    monkeypatch.setattr(land.time, "sleep", lambda s: None)
    fake = GitHub(remote)
    fake.work = work
    monkeypatch.setattr(pr_state, "gh", fake)
    return fake


def open_pr(gh, n, base, head, approved=None):
    git(gh.work, "push", "-q", "-f", "origin", f"{head}:refs/heads/task-{n}")
    gh.prs[n] = {"number": n, "branch": f"task-{n}", "base": base, "state": "OPEN", "comments": [
        {"createdAt": "2026-01-02T00:00:00Z", "author": {"login": "rev"},
         "body": f"APPROVE @ {(approved or head)[:9]}."}]}


def stack_853(gh):
    """The jgong5/ATOM#853 batch in miniature, bottom-first: #1 a linked parent with
    two rounds; #2 its linked child, cut before the second round; #3 an unlinked
    fork off #1, cut there too; #4 #2's linked child, which merged an older tip."""
    w = gh.work
    t0 = commit(w, ("f", "a"))
    git(w, "push", "-q", "origin", "dev")
    r1 = commit(w, ("x", "1"))
    open_pr(gh, 1, "dev", commit(w, ("x", "2")))
    git(w, "checkout", "-q", "-B", "t2", r1)
    a2 = commit(w, ("y", "1"))
    open_pr(gh, 2, "task-1", a2)
    git(w, "checkout", "-q", "-B", "t3", r1)
    open_pr(gh, 3, "task-1", commit(w, ("z", "1")))
    git(w, "checkout", "-q", "-B", "tip", t0)
    t1 = commit(w, ("w", "1"))
    git(w, "checkout", "-q", "-B", "t4", a2)
    commit(w, ("v", "1"))
    open_pr(gh, 4, "task-2", commit(w, merge=t1))
    git(w, "checkout", "-q", "tip")  # the tip has moved past what #4 merged
    git(w, "push", "-q", "origin", f"{commit(w, ('w', '2'))}:dev")
    gh.linked = {1, 2, 4}


def test_the_853_shaped_batch_lands_with_no_manual_step(gh):
    stack_853(gh)
    batch.main(["merge", "1", "2", "3", "4", "--record", "rec.json"])
    rec = json.loads((gh.work / "rec.json").read_text())
    assert [r["pr"] for r in rec["prs"]] == [1, 2, 3, 4]

    batch.main(["land", "--record", "rec.json", "--message-dir", "msgs"])

    assert all(p["state"] == "MERGED" for p in gh.prs.values())
    assert git(gh.work, "ls-tree", "--name-only", "-r", f"{rec['commit']}^{{tree}}").split() == [
        "f", "v", "w", "x", "y", "z"]
    assert git(gh.remote, "rev-parse", "dev^{tree}") == rec["prs"][-1]["tree"]
    # #2 landed at GitHub's rebase; #3 (base patched) and #4 (not rebased) at a base update.
    assert [c for c in gh.calls if c[:3] == ["api", "-X", "PATCH"]] == [
        ["api", "-X", "PATCH", "repos/me/proj/pulls/3", "-f", "base=dev"]]
    for n in (3, 4):
        head = gh.head(n)
        assert git(gh.remote, "log", "-1", "--format=%P", head).split()[0] == rec["prs"][n - 1]["sha"]
        assert gh.prs[n]["comments"][-1]["body"].startswith(f"Round 1 pushed {head[:9]}. ")
    assert "`x`" in gh.prs[3]["comments"][-1]["body"]
    assert len(gh.prs[2]["comments"]) == 1 and gh.head(2) != rec["prs"][1]["sha"]

    # Rerun after a stop: everything merged, nothing more happens.
    puts = len([c for c in gh.calls if c[:3] == ["api", "-X", "PUT"]])
    batch.main(["land", "--record", "rec.json", "--message-dir", "msgs"])
    assert len([c for c in gh.calls if c[:3] == ["api", "-X", "PUT"]]) == puts


def test_a_landing_outside_the_batch_stops_it_before_anything_is_pushed(gh):
    stack_853(gh)
    batch.main(["merge", "1", "2", "3", "4", "--record", "rec.json"])
    git(gh.work, "checkout", "-q", "-B", "other", "origin/dev")
    git(gh.work, "push", "-q", "origin", f"{commit(gh.work, ('o', '1'))}:dev")
    with pytest.raises(SystemExit) as e:
        batch.main(["land", "--record", "rec.json", "--message-dir", "msgs"])
    assert e.value.code == 4
    assert not [c for c in gh.calls if c[:3] == ["api", "-X", "PUT"] or c[:2] == ["pr", "comment"]]


def test_merge_refuses_a_pr_whose_base_nothing_before_it_lands(gh, capsys):
    stack_853(gh)
    with pytest.raises(SystemExit) as e:
        batch.main(["merge", "2", "--record", "rec.json"])
    assert e.value.code == 3
    assert "task-1" in capsys.readouterr().out


def test_merge_starts_from_the_tip_when_another_fetch_follows_its_own(gh, monkeypatch):
    w = gh.work
    tip = commit(w, ("f", "a"))
    git(w, "push", "-q", "origin", "dev")
    open_pr(gh, 1, "dev", commit(w, ("x", "1")))
    git(w, "checkout", "-q", "-B", "other", tip)
    git(w, "push", "-q", "origin", commit(w, ("o", "1")) + ":refs/heads/other")
    real = batch.git

    def git_then_fetch_other(*args):
        """Another command in the same worktree fetches right after batch.py's fetch."""
        out = real(*args)
        if args[0] == "fetch":
            real("fetch", "-q", "origin", "refs/heads/other")
        return out

    monkeypatch.setattr(batch, "git", git_then_fetch_other)
    batch.main(["merge", "1", "--record", "rec.json"])
    rec = json.loads((w / "rec.json").read_text())
    assert rec["tip"] == tip
    assert git(w, "ls-tree", "--name-only", "-r", rec["commit"]).split() == ["f", "x"]
