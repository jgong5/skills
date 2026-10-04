# Landing

Landing is the agents' job; no owner approval is needed or sought, and it
does not wait for `<gate_wave>`. Any PR whose `pr_state.py` turn is `land`
lands, bottom-first through a stack.

## Holds

These are the landing preconditions, and the only holds:

1. No `need human` on the PR, on any PR below it in its stack, or on an issue
   it closes.
2. An APPROVE naming each head being landed.
3. The tree check: what lands on the current tip is exactly the tree that was
   approved, or the batch tree that was gated.

A hold names the one that is unmet. **Any other rule violation seen in an
approved PR is landed and filed as an issue, not held**: the review loop is
where rules are enforced; landing only checks that what was approved is what
lands.

## Land one PR

Write the squash commit message to a scratch file: what the task does, from
the PR body, in `<publish_language>`. Then, from the main worktree:

```
python3 <skill-dir>/land.py <pr> --message-file <file>
```

It refuses on an overlay problem (exit 2), a hold (exit 3), or a tree that
would land other than the approved one (exit 4). Otherwise it squashes the
approved sha through GitHub's merge-async endpoint, with the title ending
` (#<pr>)` (that endpoint does not add it), and polls until GitHub reports
the merge (exit 0). Exit 5 -- a failed merge, a merge queue taking the PR
instead, or a timeout -- is a finding to diagnose, never to retry blind. For a stacked child whose parent has landed, pass
`--merge-base <parent's approved head>`: the parent landed as a new squash
commit, and without it the plain merge reports conflicts that do not exist.

## Land a batch

Every landing moves the tip, so the next approved PR's tree check fails even
when nothing conflicts. Two green PRs can still merge red, so the combined
tree must be gated, but once, not once per PR:

1. In a detached scratch worktree at the tip, merge the approved heads in
   landing order (bottom-first through each stack), recording
   `git rev-parse HEAD^{tree}` after each merge.
2. Run `<gate_task>` on the final tree. Red is a finding: land nothing from
   the batch, and bisect it by gating smaller prefixes.
3. Land each PR in order with `--expect-tree <its recorded tree>`.

A conflict while merging the batch sends that PR back to its developer
(merge the tip into the branch, `rules.md` Branches), followed by a delta
review of the resolution.

## After landing

- Fast-forward the main worktree's local `<integration_branch>`, which
  project tooling may diff against: `git fetch <remote>
  <integration_branch>:<integration_branch>` from the main worktree. Git
  refuses that while some worktree has the branch checked out; run `git fetch
  <remote> && git merge --ff-only <remote>/<integration_branch>` in that
  worktree instead. Then
  apply whatever the overlay body says follows a git update.
- Close the delivered issue with a handoff comment, drawn from the Dev
  record's "left undone" and the review record's "watch next". A PR into a
  non-default branch does not close its issue on GitHub's own.
- Close any umbrella issue whose sub-tasks have all landed, with a handoff.
- An issue that depended on this one may now be claimable; the next `run`
  pass picks it up.
- When a `run` has landed anything and `<gate_wave>` is set, run it once on
  the new tip before the final report. It is judged as a delta: if it is
  red, run it on the tip from before this run's first landing, and file
  each failure that is new as a finding issue.

## Stacking

Recommended, not required: stack a dependent task's PR on its unlanded
parent with `gh stack` (the `github/gh-stack` extension); independent tasks
do not stack.

- Link a chain whole or not at all, and only when you mean it (`gh stack
  unstack` can refuse):
  `gh stack link --base <integration_branch> <bottom-pr> ... <top-pr>`, re-run
  whenever a PR joins, held members included (linking lands nothing). Only
  linked members are retargeted when a parent lands. A fork (two or more open
  PRs based on one open PR's branch) links at most one arm. Drift check:
  every open PR based on another open PR's branch sits in one stack, fork
  arms excepted (`gh api "repos/<repo>/stacks?pull_request=<n>"`).
- Land a stack one PR at a time with `land.py`, never with `gh stack merge`:
  it takes no message and force-pushes the child after landing. Never run
  `gh stack rebase`, `sync`, `push` or `submit` either; each rebases or
  force-pushes (`rules.md`, Branches).
- When a parent lands, GitHub retargets a linked child itself. An unlinked
  child (a fork arm, or a chain never linked) gets its base patched
  (`gh api -X PATCH repos/<repo>/pulls/<child> -f base=<integration_branch>`)
  and the new tip merged into it, so its diff shows only its own changes,
  then gets the round comment that `rules.md` (Branches) requires.
