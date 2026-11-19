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
    assert lint_gh_prose.lint(text, "comment") == ["line 6: private ref (link it or say it): '\u00a7'"]


def test_a_details_tag_in_inline_code_hides_nothing():
    text = "Closes #1.\nThe `<details>` block.\nsee \u00a7 3\n<details>x</details>\n"
    assert lint_gh_prose.lint(text, "comment") == ["line 3: private ref (link it or say it): '\u00a7'"]


def test_a_closing_tag_in_inline_code_does_not_end_a_block():
    text = "Closes #1.\n<details>\nthe `</details>` tag\nsee \u00a7 3\n</details>\n"
    assert lint_gh_prose.lint(text, "comment") == []


def test_an_unclosed_block_of_inline_code_does_not_hang():
    text = "Closes #1.\n<details>\n" + "`a` " * 40 + "\n"
    assert lint_gh_prose.lint(text, "comment") == []


def test_a_block_opened_mid_list_item_does_not_split_the_list():
    text = "Closes #1.\n- a\n- b\n- c <details>\nx\n</details>\n- d\n- e\n- f\n- g\n"
    assert lint_gh_prose.lint(text, "comment") == ["list/table of 7 lines, max 5 items"]


@pytest.mark.parametrize("first", ["**Ruling**: (a).", "**Ruling:** (a)."])
def test_a_bold_ruling_is_flagged(first):
    assert lint_gh_prose.lint(first, "comment")
    assert lint_gh_prose.lint("Ruling: (a).", "comment") == []
    assert lint_gh_prose.lint("Ruling on #9 affects this: x.", "comment") == []
    assert lint_gh_prose.lint("**Ruling request**: x.", "comment") == []


def test_a_brief_update_states_its_state():
    assert lint_gh_prose.lint("Brief updated: Fix. <link>", "comment") == []
    link = "https://github.com/jgong5/skills/issues/171"
    assert lint_gh_prose.lint(f"Brief updated: Fix. {link}", "comment") == []


def test_a_bold_needs_owner_ruling_label_is_flagged():
    assert lint_gh_prose.lint("**Needs owner ruling**: keep the cut?", "comment")
    assert lint_gh_prose.lint("**Needs owner ruling:** keep the cut?", "comment") == []
    assert lint_gh_prose.lint("Needs owner ruling: keep the cut?", "comment") == []


def test_a_request_naming_its_ruler_states_its_state():
    assert lint_gh_prose.lint("Needs ruling from @bob: keep the cut or split #38?", "comment") == []


def test_a_ruler_without_an_at_is_no_login():
    hits = lint_gh_prose.lint("Needs ruling from bob: keep the cut or split #38?", "comment")
    assert hits == ["first line states no state or ask: 'Needs ruling from bob: keep the cut or split #38?'"]


PR = "Closes #1. Ready for review.\n## Why\nIt broke.\n## What changed\nIt works.\n## Review focus\nnone\n## Testing\nA test.\n## Follow-ups\nnone\n"


def test_a_pr_body_in_the_shape_is_clean():
    assert lint_gh_prose.lint(PR, "pr") == []


def test_a_pr_heading_out_of_order_is_flagged():
    text = PR.replace("## Why\nIt broke.\n", "").replace("## Testing", "## Why\nIt broke.\n## Testing")
    assert lint_gh_prose.lint(text, "pr") == [
        "headings ['What changed', 'Review focus', 'Why', 'Testing', 'Follow-ups'], "
        "want exactly ['Why', 'What changed', 'Review focus', 'Testing', 'Follow-ups'] in that order"
    ]


def test_a_pr_heading_folded_in_details_is_missing():
    text = PR.replace("## Follow-ups\nnone\n", "<details>\n\n## Follow-ups\nnone\n</details>\n")
    assert lint_gh_prose.lint(text, "pr") == ["missing heading: ## Follow-ups"]


def test_a_code_span_is_flagged_under_why_only():
    assert lint_gh_prose.lint(PR.replace("It broke.", "`f` broke."), "pr") == [
        "code span under ## Why: say the behaviour in words"
    ]
    assert lint_gh_prose.lint(PR.replace("It works.", "`f` works."), "pr") == []


def test_an_issue_reference_opening_a_why_line_does_not_end_why():
    assert lint_gh_prose.lint(PR.replace("It broke.", "#12 broke it.\n`f` too."), "pr") == [
        "code span under ## Why: say the behaviour in words"
    ]


def test_a_visible_sentence_over_35_words_is_flagged():
    long = "a " * 35 + "\nb."  # wrapped over two lines, still one sentence
    assert lint_gh_prose.lint(PR.replace("It works.", long), "pr") == [
        "sentence of 36 words, max 35: " + repr(long[:60])
    ]
    assert lint_gh_prose.lint(PR.replace("It works.", long[2:]), "pr") == []
    assert lint_gh_prose.lint(PR + f"<details>{long}</details>\n", "pr") == []


def test_list_items_without_periods_are_separate_sentences():
    items = ("- " + "a " * 20 + "\n") * 2
    assert lint_gh_prose.lint(PR.replace("It works.\n", items), "pr") == []


def test_a_mermaid_fence_over_30_lines_is_flagged():
    fence = lambda n: "```mermaid\n" + "a-->b\n" * n + "```\n"
    text = lambda n: PR.replace("It works.", fence(n) + "It works.")
    assert lint_gh_prose.lint(text(31), "pr") == ["mermaid diagram of 31 lines, max 30"]
    assert lint_gh_prose.lint(text(30), "pr") == []
