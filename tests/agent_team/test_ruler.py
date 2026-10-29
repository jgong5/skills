import json

import pytest

import ruler

URL = "https://github.com/o/r"


def comment(at, body, n, k):
    return {"createdAt": at, "body": body, "url": f"{URL}/issues/{n}#issuecomment-{k}"}


def issue(n, assignees=(), comments=()):
    return {"number": n, "title": "Brief", "body": "", "url": f"{URL}/issues/{n}",
            "assignees": [{"login": a} for a in assignees], "comments": list(comments)}


def pr(n, title="Work", body="", assignees=(), comments=()):
    return dict(issue(n, assignees, comments), title=title, body=body, url=f"{URL}/pull/{n}")


@pytest.fixture
def fake_gh(monkeypatch):
    """Serve `gh issue view N` from .items[N], `gh pr list` from the PRs there, reviews from .reviews[N]."""
    class Fake:
        items, reviews = {}, {}

        def __call__(self, args, check=True):
            if args[:2] == ["issue", "view"]:
                return json.dumps(self.items[int(args[2])])
            if args[:2] == ["pr", "list"]:
                return json.dumps([i for i in self.items.values() if "/pull/" in i["url"]])
            if args[0] == "api":
                return json.dumps(self.reviews.get(int(args[1].split("/")[-2]), []))
            raise AssertionError(args)

    fake = Fake()
    monkeypatch.setattr(ruler, "gh", fake)
    return fake


def test_a_lone_assignee_rules_an_issue_with_no_request(fake_gh):
    fake_gh.items = {5: issue(5, ["alice"], [comment("2026-01-01T00:00:00Z", "Claimed: branch task-5.", 5, 1)])}
    assert ruler.ruler(5) == {"item": 5, "ruler": "alice", "source": "assignee",
                              "assignees": ["alice"], "request": None}


def test_no_assignee_or_several_leave_the_ruler_null(fake_gh):
    fake_gh.items = {5: issue(5)}
    assert ruler.ruler(5)["source"] == "unassigned" and ruler.ruler(5)["ruler"] is None
    fake_gh.items = {5: issue(5, ["alice", "bob"])}
    r = ruler.ruler(5)
    assert (r["ruler"], r["source"], r["assignees"]) == (None, "multiple-assignees", ["alice", "bob"])


def test_a_request_naming_a_login_overrides_the_assignee(fake_gh):
    ask = comment("2026-01-02T00:00:00Z", "**Needs ruling from @carol:** which API?", 5, 2)
    fake_gh.items = {5: issue(5, ["alice"], [ask])}
    assert ruler.ruler(5) == {"item": 5, "ruler": "carol", "source": "request",
                              "assignees": ["alice"], "request": ask["url"]}


def test_the_latest_request_wins_and_an_owner_request_falls_back_to_the_assignee(fake_gh):
    later = comment("2026-01-03T00:00:00Z", "Needs owner ruling: which API?", 5, 3)
    fake_gh.items = {5: issue(5, ["alice"], [
        later, comment("2026-01-02T00:00:00Z", "Needs ruling from @carol: which API?", 5, 2)])}
    r = ruler.ruler(5)
    assert (r["ruler"], r["source"], r["request"]) == ("alice", "assignee", later["url"])


def test_a_request_in_a_delivering_prs_thread_counts_and_a_notice_does_not(fake_gh):
    fake_gh.items = {
        5: issue(5, ["alice"]),
        8: pr(8, body="Closes #5.", comments=[
            comment("2026-01-02T00:00:00Z", "Needs ruling from @carol: keep it?", 8, 2),
            comment("2026-01-04T00:00:00Z", "Ruling on #5 affects this: re-review.", 8, 4)]),
        9: pr(9, title="Something else (#6)", comments=[
            comment("2026-01-05T00:00:00Z", "Needs ruling from @dave: unrelated", 9, 5)]),
    }
    r = ruler.ruler(5)
    assert (r["ruler"], r["request"]) == ("carol", f"{URL}/issues/8#issuecomment-2")
    # A review counts, and a PR named in the title delivers as much as one named in the body.
    fake_gh.items[9]["title"] = "agent-team: add a thing (#5)"
    fake_gh.reviews = {9: [{"submitted_at": "2026-01-03T00:00:00Z", "html_url": f"{URL}/pull/9#r1",
                            "body": "Needs ruling from @erin: merge or split?"},
                           {"submitted_at": None, "html_url": f"{URL}/pull/9#r2",
                            "body": "Needs ruling from @frank: pending, not posted"}]}
    fake_gh.items[9]["comments"] = []
    assert ruler.ruler(5)["ruler"] == "erin"


def test_a_pr_stands_for_the_issue_it_delivers_or_for_itself(fake_gh):
    fake_gh.items = {5: issue(5, ["alice"]), 8: pr(8, body="Fixes #5.", assignees=["bob"])}
    assert ruler.ruler(8)["item"] == 5 and ruler.ruler(8)["ruler"] == "alice"
    fake_gh.items = {8: pr(8, body="Part of #5.", assignees=["bob"])}
    assert ruler.ruler(8) == {"item": 8, "ruler": "bob", "source": "assignee",
                              "assignees": ["bob"], "request": None}


def test_a_pr_delivering_several_issues_exits_2_naming_them(fake_gh, capsys):
    fake_gh.items = {8: pr(8, title="Fix #4", body="Closes #5. Resolves #6.")}
    with pytest.raises(SystemExit) as e:
        ruler.ruler(8)
    assert e.value.code == 2
    assert "#4, #5, #6" in capsys.readouterr().err

