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


@pytest.mark.parametrize("label", ["agent-team/need-human", "need human"])
def test_either_name_of_the_need_human_label_holds_every_turn_and_is_named(fake_gh, label):
    # A round comment alone would make it the reviewer's turn.
    fake_gh.pr = make_pr([ROUND], labels=[label])
    s = pr_state.state(7)
    assert s["turn"] == "held" and f"{label} on the PR" in s["holds"]
    fake_gh.pr, fake_gh.issues = make_pr([ROUND], closes=[4]), {4: [label]}
    s = pr_state.state(7)
    assert s["turn"] == "held" and f"{label} on issue #4, which this PR delivers" in s["holds"]


@pytest.mark.parametrize("label", ["agent-team/hold-landing", "hold landing"])
def test_either_name_of_the_hold_landing_label_holds_only_the_land_turn(fake_gh, label):
    approved = [comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")]
    fake_gh.pr, fake_gh.issues = make_pr(approved, closes=[4]), {4: [label]}
    s = pr_state.state(7)
    assert s["turn"] == "held" and s["holds"] == [f"{label} on issue #4, which this PR delivers"]
    fake_gh.pr = make_pr([ROUND], labels=[label])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and f"{label} on the PR" in s["holds"]


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


def test_hold_landing_holds_only_the_land_turn(fake_gh):
    approved = [comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")]
    fake_gh.pr = make_pr(approved, labels=["hold landing"])
    s = pr_state.state(7)
    assert s["turn"] == "held" and s["holds"] == ["hold landing on the PR"]
    fake_gh.pr, fake_gh.issues = make_pr(approved, closes=[4]), {4: ["hold landing"]}
    s = pr_state.state(7)
    assert s["turn"] == "held" and s["holds"] == ["hold landing on issue #4, which this PR delivers"]
    # Developer and reviewer turns go on under it.
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "REQUEST CHANGES @ c0ffee1.", "rev")],
                         labels=["hold landing"])
    assert pr_state.state(7)["turn"] == "developer"
    fake_gh.pr = make_pr([ROUND], labels=["hold landing"])
    assert pr_state.state(7)["turn"] == "reviewer"


def test_an_approve_at_another_sha_covers_the_head_only_when_the_caller_says_so(fake_gh):
    asked = []
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "APPROVE @ 1111111.", "rev")])
    s = pr_state.state(7, equivalent=lambda sha, head: asked.append((sha, head)) or True)
    assert s["turn"] == "land" and s["holds"] == [] and asked == [("1111111", HEAD)]
    s = pr_state.state(7, equivalent=lambda sha, head: False)
    assert s["turn"] == "developer" and "delta review needed" in s["holds"][0]
    # A REQUEST CHANGES at another sha is never carried forward.
    fake_gh.pr = make_pr([comment("2026-01-02T00:00:00Z", "REQUEST CHANGES @ 1111111.", "rev"), ROUND])
    assert pr_state.state(7, equivalent=lambda sha, head: True)["turn"] == "reviewer"


def test_a_ruling_restarts_the_verdict_count(fake_gh):
    rc = [comment(f"2026-01-0{d}T00:00:00Z", f"REQUEST CHANGES @ 111111{d}: 1 blocking.", "rev")
          for d in (2, 3, 4)]
    ruling = comment("2026-01-06T00:00:00Z", "**Ruling:** (a) keep the cut.", "owner")
    last = comment("2026-01-07T00:00:00Z", "REQUEST CHANGES @ c0ffee1: 1 blocking.", "rev")
    fake_gh.pr = make_pr(rc + [last])
    before = pr_state.state(7)
    assert before["verdicts"] == 4
    fake_gh.pr = make_pr(rc + [ruling, last])
    s = pr_state.state(7)
    assert s["verdicts"] == 1 and s["verdict"] == before["verdict"]
    # A REQUEST CHANGES before the ruling is still the last verdict.
    fake_gh.pr = make_pr(rc[:2] + [comment("2026-01-04T00:00:00Z", "REQUEST CHANGES @ c0ffee1.", "rev"), ruling])
    s = pr_state.state(7)
    assert s["verdicts"] == 0 and s["verdict"]["sha"] == "c0ffee1"


def test_a_ruling_after_request_changes_is_the_reviewers_turn(fake_gh):
    # The ruling may leave nothing to push, so a fresh verdict under it comes first.
    rc = comment("2026-01-02T00:00:00Z", "REQUEST CHANGES @ c0ffee1: 1 blocking.", "rev")
    ruling = comment("2026-01-03T00:00:00Z", "Ruling: (a) accept as is.", "owner")
    fake_gh.pr = make_pr([rc, ruling])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and s["verdicts"] == 0
    fake_gh.pr = make_pr([dict(ruling, createdAt="2026-01-01T12:00:00Z"), rc])
    assert pr_state.state(7)["turn"] == "developer"


def test_a_ruling_after_an_approve_is_the_reviewers_turn(fake_gh):
    # The ruling may have changed the brief the APPROVE was given against.
    approve = comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")
    affects = comment("2026-01-03T00:00:00Z", "Ruling on #9 affects this: it now waits for #45.", "owner")
    fake_gh.pr = make_pr([approve, affects])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and s["holds"] == ["a ruling follows the last verdict"]
    assert s["verdicts"] == 1  # only `Ruling:` restarts the count
    fake_gh.pr = make_pr([approve, dict(affects, body="Ruling: (a) accept as is.")])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and s["verdicts"] == 0
    fake_gh.pr = make_pr([dict(affects, createdAt="2026-01-01T12:00:00Z"), approve])
    s = pr_state.state(7)
    assert s["turn"] == "land" and s["holds"] == []


def test_a_brief_update_after_the_round_comment_is_the_developers_turn(fake_gh):
    # jgong5/ATOM#2610: the brief changed under an announced head, so code answers it first.
    round1 = comment("2026-01-02T00:00:00Z", "Round 1 pushed c0ffee1.")
    ruling = comment("2026-01-03T00:00:00Z", "Ruling: https://x/2600#c1. Brief updated: Fix.", "owner")
    fake_gh.pr = make_pr([round1, ruling])
    s = pr_state.state(7)
    assert s["turn"] == "developer" and "a brief update follows the last verdict" in s["holds"]
    # A later comment naming the head, the same sha included, hands it back.
    fake_gh.pr["comments"].append(comment("2026-01-04T00:00:00Z", "Round 2 pushed c0ffee1."))
    assert pr_state.state(7)["turn"] == "reviewer"


def test_a_brief_update_holds_an_approve_and_reads_past_the_first_line(fake_gh):
    approve = comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")
    notice = comment("2026-01-03T00:00:00Z", "See #9.\n<link>\nBrief updated: Depends on.")
    fake_gh.pr = make_pr([approve, notice])
    assert pr_state.state(7)["turn"] == "developer"
    fake_gh.pr["comments"].append(comment("2026-01-04T00:00:00Z", "Round 2 pushed c0ffee1: nothing to change."))
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and "a brief update follows the last verdict" in s["holds"]
    # Case-sensitive, colon required, and only after the last verdict.
    for body in ("brief updated: Fix.", "Brief updated Fix."):
        fake_gh.pr = make_pr([approve, comment("2026-01-03T00:00:00Z", body)])
        assert pr_state.state(7)["turn"] == "land"
    fake_gh.pr = make_pr([comment("2026-01-01T00:00:00Z", "Brief updated: Fix."), approve])
    assert pr_state.state(7)["turn"] == "land"


def test_a_brief_update_quoted_as_code_is_not_one(fake_gh):
    # jgong5/skills#231: a round comment quoting the pointer form held landing.
    approve = comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")
    for body in ("Round 2 pushed c0ffee1. It posts `` `Brief updated: x.` `` on each PR.",
                 "Quoting `Brief updated: x.` here.",
                 "It posts `Ruling: <link>. Brief updated: x.` on each PR.",
                 "Round 2 pushed c0ffee1. The notice:\n\n```\nBrief updated: x.\n```\n"):
        fake_gh.pr = make_pr([approve, comment("2026-01-03T00:00:00Z", body)])
        s = pr_state.state(7)
        assert s["turn"] == "land" and s["holds"] == [], body
    # Unquoted, beside a code span, it still is one.
    fake_gh.pr = make_pr([approve, comment("2026-01-03T00:00:00Z", "See `x`.\nBrief updated: Fix.")])
    s = pr_state.state(7)
    assert s["turn"] == "developer" and "a brief update follows the last verdict" in s["holds"]


def test_an_ai_ruling_after_an_approve_is_a_ruling(fake_gh):
    approve = comment("2026-01-02T00:00:00Z", "APPROVE @ c0ffee1.", "rev")
    ruling = comment("2026-01-03T00:00:00Z", "**Ruling (auto):** (a) keep the cut.", "bot")
    fake_gh.pr = make_pr([approve, ruling])
    s = pr_state.state(7)
    assert s["turn"] == "reviewer" and s["verdicts"] == 0
    assert s["holds"] == ["a ruling follows the last verdict"]
    # Only that opening: anything else after `Ruling` is not a Ruling.
    fake_gh.pr = make_pr([approve, dict(ruling, body="Ruling (draft): (a) keep the cut.")])
    s = pr_state.state(7)
    assert s["turn"] == "land" and s["verdicts"] == 1


def test_an_ai_ruling_restarts_the_verdict_count(fake_gh):
    rc = [comment(f"2026-01-0{d}T00:00:00Z", f"REQUEST CHANGES @ 111111{d}: 1 blocking.", "rev")
          for d in (2, 3, 4)]
    ruling = comment("2026-01-06T00:00:00Z", "Ruling (auto): (b) split the task.", "bot")
    last = comment("2026-01-07T00:00:00Z", "REQUEST CHANGES @ c0ffee1: 1 blocking.", "rev")
    fake_gh.pr = make_pr(rc + [ruling, last])
    assert pr_state.state(7)["verdicts"] == 1
