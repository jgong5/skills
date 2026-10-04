import json

import pytest

import pr_state

HEAD = "c0ffee1234567890c0ffee1234567890c0ffee12"


def comment(at, body, who="dev"):
    return {"createdAt": at, "author": {"login": who}, "body": body}


def make_pr(comments=(), reviews=(), labels=(), closes=(), state="OPEN", head=HEAD, body=""):
    return {
        "number": 7, "state": state, "body": body, "headRefOid": head, "baseRefName": "dev",
        "labels": [{"name": n} for n in labels],
        "comments": list(comments), "reviews": list(reviews),
        "commits": [{"committedDate": "2026-01-01T00:00:00Z", "oid": head}],
        "closingIssuesReferences": [{"number": n} for n in closes],
    }


ROUND = comment("2026-01-05T00:00:00Z", "Round 2 pushed c0ffee1.")


@pytest.fixture
def fake_gh(monkeypatch):
    """Serve `gh pr view` from .pr and `gh issue view N` from .issues[N]."""
    class Fake:
        pr, issues = make_pr(), {}

        def __call__(self, args, check=True):
            if args[:2] == ["pr", "view"]:
                return json.dumps(self.pr)
            if args[:2] == ["issue", "view"]:
                return json.dumps({"labels": [{"name": n} for n in self.issues.get(int(args[2]), ())]})
            raise AssertionError(args)

    fake = Fake()
    monkeypatch.setattr(pr_state, "gh", fake)
    return fake


def test_an_approve_naming_the_head_means_land(fake_gh):
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "**APPROVE** @ c0ffee1.", "rev")])
    s = pr_state.state(7)
    assert s["holds"] == [] and s["turn"] == "land"
    assert s["verdict"]["sha"] == "c0ffee1"


def test_a_head_past_the_approval_needs_a_delta_review(fake_gh):
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "APPROVE @ 1111111.", "rev"), ROUND])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer"
    assert "delta review needed" in s["holds"][0]


def test_a_head_past_a_request_changes_needs_the_whole_head_reviewed(fake_gh):
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "REQUEST CHANGES @ 1111111: 1 blocking.", "rev"),
                          ROUND])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer"
    assert s["holds"][0].endswith("review the whole head")


def test_the_last_verdict_wins_and_a_later_round_is_the_last_entry(fake_gh):
    fake_gh.pr = make_pr([
        comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev"),
        comment("2026-01-03T00:00:00Z", "## REQUEST CHANGES @ c0ffee1: 1 blocking.", "rev"),
        comment("2026-01-04T00:00:00Z", "Round 2 pushed c0ffee1."),
    ])
    s = pr_state.state(7)
    assert s["verdict"]["verdict"] == "REQUEST CHANGES" and s["verdicts"] == 2
    assert s["turn"] == "developer"
    assert s["last_entry"]["line"] == "Round 2 pushed c0ffee1."


def test_a_review_body_counts_and_approved_is_not_approve(fake_gh):
    fake_gh.pr = make_pr(
        [comment("2026-01-03T00:00:00Z", "APPROVED by the team lead, see below", "x")],
        reviews=[{"submittedAt": "2026-01-02T00:00:00Z", "author": {"login": "rev"},
                  "body": "APPROVE @ c0ffee1."}])
    s = pr_state.state(7)
    assert s["verdict"]["author"] == "rev" and s["turn"] == "land"


def test_need_human_on_the_pr_or_on_an_issue_it_closes_holds_it(fake_gh):
    approved = [comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")]
    fake_gh.pr = make_pr(approved, labels=["need human"])
    assert pr_state.state(7)["turn"] == "held"
    fake_gh.pr, fake_gh.issues = make_pr(approved, closes=[3, 4]), {4: ["need human"]}
    s = pr_state.state(7)
    assert s["turn"] == "held"
    assert s["holds"] == ["need human on issue #4, which this PR delivers"]


def test_an_issue_named_by_a_delivering_verb_in_the_body_holds_it_too(fake_gh):
    # Into a non-default branch GitHub records no closing reference at all.
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")],
                         body="Implements #9. Part of #4, see #4.")
    fake_gh.issues = {4: ["need human"], 9: ["need human"]}
    assert pr_state.state(7)["holds"] == ["need human on issue #9, which this PR delivers"]


def test_no_verdict_or_a_verdict_without_a_sha_is_the_reviewers_turn(fake_gh):
    fake_gh.pr = make_pr([ROUND])
    assert pr_state.state(7)["holds"] == ["no verdict yet"]
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "APPROVE.", "rev"), ROUND])
    s = pr_state.state(7)
    assert s["holds"] == ["the last verdict names no sha"] and s["turn"] == "reviewer"


def test_a_pending_review_is_not_in_the_thread(fake_gh):
    # GitHub leaves submittedAt null on a review not yet submitted.
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")],
                         reviews=[{"submittedAt": None, "author": {"login": "rev"},
                                   "body": "REQUEST CHANGES @ c0ffee1: 1 blocking."}])
    assert pr_state.state(7)["turn"] == "land"


def test_a_pushed_head_is_the_reviewers_turn_only_once_a_round_comment_names_it(fake_gh):
    rc = comment("2026-01-02T00:00:00Z", "REQUEST CHANGES @ 1111111: 1 blocking.", "rev")
    for before in ([], [rc]):
        # A comment naming an older head does not announce this one.
        fake_gh.pr = make_pr(before + [comment("2026-01-03T00:00:00Z", "Round 1 pushed 1111111.")])
        s = pr_state.state(7)
        assert s["turn"] == "developer"
        assert s["holds"][-1].endswith("no round comment")
        fake_gh.pr["comments"].append(ROUND)
        s = pr_state.state(7)
        assert s["turn"] == "reviewer" and not any("round comment" in h for h in s["holds"])
    # Nor does one posted before the last verdict.
    fake_gh.pr = make_pr([ROUND, comment("2026-01-06T00:00:00Z", "REQUEST CHANGES @ 1111111.", "rev")])
    assert pr_state.state(7)["turn"] == "developer"
