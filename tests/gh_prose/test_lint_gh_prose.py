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


def test_a_details_tag_in_inline_code_hides_nothing():
    text = "Closes #1.\nThe `<details>` block.\nsee \u00a7 3\n<details>x</details>\n"
    assert lint_gh_prose.lint(text, "pr") == ["line 3: private ref (link it or say it): '\u00a7'"]


def test_a_closing_tag_in_inline_code_does_not_end_a_block():
    text = "Closes #1.\n<details>\nthe `</details>` tag\nsee \u00a7 3\n</details>\n"
    assert lint_gh_prose.lint(text, "pr") == []


def test_a_block_opened_mid_list_item_does_not_split_the_list():
    text = "Closes #1.\n- a\n- b\n- c <details>\nx\n</details>\n- d\n- e\n- f\n- g\n"
    assert lint_gh_prose.lint(text, "pr") == ["list/table of 7 lines, max 5 items"]
