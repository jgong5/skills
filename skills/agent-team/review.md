# Reviewer

You review one PR at its current head and post one verdict. You were given
the PR number, the overlay keys and body, and this skill's directory.

## 1. Read

Read `<design_entry>` first, then `rules.md`, the issue's brief, the PR body
and its whole thread. Run `python3 <skill-dir>/pr_state.py <pr> --repo
<repo>`. Its `head` is the sha you review. If the thread's last APPROVE named
an older sha, this is a **delta review** (step 3).

## 2. Check

Check in your own worktree or `git archive` snapshot of the head, never in
the developer's tree, and run `<import_check>` there when it is set.

- **Gates 1-3** (`develop.md`, Pass the gates), as they apply to this task:
  run `<gate_task>` yourself; confirm no existing test was edited without a
  justification in the Dev record; confirm the new tests reach code the PR
  did not add; confirm the brief's named result, the one it stated, is shown.
- **Credit a test with holding a defect only after you have seen it red**:
  reinstate the pre-fix code (`git show`, line count preserved, nothing else
  changed), run it, and record both counts and the failing test id and
  assertion. **An inert pin on a required finding blocks APPROVE.**
- The published-text rules (`rules.md`) over the PR's whole file set at its
  head, not only the added lines.
- Run the `ponytail-review` skill over the diff when it is installed, to catch
  over-engineering; post its findings like any others.

Approving is gate 4. A finding is blocking when the task cannot land without
its fix; say which findings block. **A review blocks only on what the PR's
change gets wrong or its brief requires.** A pre-existing defect you happen
to see goes under `Watch next:` in one line, and gets an issue only when it
would make a reader or a test reach a wrong conclusion: otherwise each
review finds an older neighbour and the pool keeps growing.

## 3. Delta review

An approval covers a tree, not a PR. When the head has moved past the sha the
last APPROVE named, review only the new commits:

```
git log -p --first-parent --diff-merges=remerge <approved sha>..<head>
```

That shows each commit's own diff, and only the conflict resolutions of each
merge. What a merge brings in is reviewed in its own PR.

## 4. Post

- A finding that points at lines is an inline comment:
  `gh api repos/<repo>/pulls/<pr>/comments -f body=... -f commit_id=<head>
  -f path=<path> -F line=<line>`, worded `<problem>. <fix>.`
- The verdict is one standalone PR comment, not a GitHub review: every agent
  posts as the same account, and GitHub refuses APPROVE or REQUEST_CHANGES
  on a self-authored PR. Its first line is `APPROVE @ <head sha>.` or
  `REQUEST CHANGES @ <head sha>: <k> blocking.` -- the sha is what lets
  `pr_state.py` tell whether the verdict still covers the head. Then the
  review record (`gh-prose`): `Checked:`, `Accepted with reservation:`,
  `Watch next:`, and the findings that have no line.

## 5. The loop's own stop

If the same finding survives two cycles, or this would be the fourth verdict
without an APPROVE, do not post another round: escalate (`rules.md`) and
apply `need human` to the PR. A task that cannot converge is mis-cut, not
under-worked.

**Done when** a verdict comment naming the current head is posted, or the
loop's stop has escalated the PR.
