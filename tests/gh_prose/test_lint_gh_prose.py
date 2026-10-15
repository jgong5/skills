"""Every bad sample must draw a hit and every good one none. Name: <name>.<kind>.md"""

from pathlib import Path

import pytest

import lint_gh_prose

SAMPLES = sorted((Path(__file__).parent / "samples").glob("*/*.md"))


def test_imported_this_skills_copy():
    assert Path(lint_gh_prose.__file__).parent.name == "gh-prose"


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_sample(path):
    kind = path.stem.rsplit(".", 1)[1]
    hits = lint_gh_prose.lint(path.read_text(encoding="utf-8"), kind)
    assert bool(hits) == (path.parent.name == "bad"), hits


def test_a_claim_comment_states_its_state():
    assert lint_gh_prose.lint("Claimed: worktree ../r-worktrees/12, branch task-12.", "comment") == []


def test_a_review_verdict_names_the_head_it_covers():
    assert lint_gh_prose.lint("REQUEST CHANGES: 1 blocking.", "review")
    assert lint_gh_prose.lint("**APPROVE** @ c0ffee1.", "review") == []


@pytest.mark.parametrize("block", ["<details>\na\nb\n</details>", "```\na\nb\n```"])
def test_a_hit_below_a_stripped_block_reports_its_file_line(block):
    text = f"Closes #1.\n{block}\nsee \u00a7 3\n"
    assert lint_gh_prose.lint(text, "pr") == ["line 6: private ref (link it or say it): '\u00a7'"]
