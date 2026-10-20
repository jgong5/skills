# Landing

Landing is the agents' job; no owner approval is needed or sought, and it
does not wait for `<gate_wave>`. Any PR whose `pr_state.py` turn is `land`
lands, bottom-first through a stack.

## Holds

These are the landing preconditions, and the only holds:

1. No `need human` on the PR, on any PR below it in its stack, or on an issue
   it closes.
2. An APPROVE naming each head being landed, or, in a batch, an APPROVE
   at another sha that lands as the same gated tree, or whose base update
   carries it (Land a batch).
3. The tree check: what lands on the current tip is exactly the tree that was
   approved, or the batch tree that was gated.
4. No `hold landing` on the PR or on an issue it closes. It holds landing and
   nothing else -- development and review go on -- and whoever applied it
   removes it.
5. No entry after the last verdict whose first line opens with `Ruling:` or
   `Ruling on #N affects this:`. The ruling may have changed the brief, so a
   fresh verdict under it comes first.

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
instead, or a timeout -- is a finding to diagnose, never to retry blind.

The tree check is GitHub's own merge of the head onto the tip, because that
is the merge that lands: GitHub takes no merge base. So a stacked child
whose parent has landed as a new squash commit can fail it with nothing
real to resolve. Land such a child through `batch.py`, alone if need be
(Land a batch), which gives it the base update it needs.

A PR labeled `land as merge` lands as a two-parent merge commit instead,
whose second parent is the approved head, under the same holds, tree check
and `--expect-tree`; the message file becomes the merge commit's message.
Use it only for a branch whose history must survive landing, such as a merge
of an upstream repository: squashed, the upstream commit stops being an
ancestor, so the next upstream merge conflicts on everything since and `git
log` loses the upstream history.

## Land a batch

Every landing moves the tip, so the next approved PR's tree check fails even
when nothing conflicts. Two green PRs can still merge red, so the combined
tree must be gated, but once, not once per PR. From the main worktree, with
the PRs in landing order (bottom-first through each stack):

1. `python3 <skill-dir>/batch.py merge <pr>... --record <file>` merges
   each approved head onto the tip as local commits, never pushed, and
   writes to the record each PR's approved sha, merge base and tree. It
   prints the batch commit. It refuses on a hold, on a PR whose base is
   neither `<integration_branch>` nor an earlier PR's branch (both exit 3),
   and on a conflict (exit 4).
2. Run `<gate_task>` on the batch commit, in a detached scratch worktree
   (`git worktree add --detach <path> <commit>`). Red is a finding: land
   nothing from the batch, and bisect it by gating smaller prefixes.
3. `python3 <skill-dir>/batch.py land --record <file> --message-dir <dir>`,
   with one `<pr>.txt` per PR written as for Land one PR, lands each PR in
   order through `land.py` with `--expect-tree <its recorded tree>`.

Before each PR, `batch.py land` stops (exit 4) if the tip's tree is not the
batch's tree below that PR -- something outside the batch has landed, so the
gate no longer covers it; merge again. It gives GitHub a moment to retarget
and rebase a linked child of a PR it landed, and patches an unlinked
child's base to `<integration_branch>` itself. Where GitHub's merge of the
approved head would not give the recorded tree, it pushes a base update: a
commit whose parents are the approved head and the tip and whose tree is
the recorded one, with the round comment `rules.md` (Branches) requires,
naming each file the batch merge resolved. It skips a merged PR, so after a
stop, rerunning `land` resumes. Its exits are `land.py`'s.

The batch tree, not a PR's own review of its head, is what licenses the
landing. Under `--expect-tree`, `land.py` accepts the APPROVE at an older
sha in two cases. A GitHub rebase -- a new head with the same content --
passes when merging the old sha onto the tip, based on `--merge-base`, and
merging the new head onto the tip both give the recorded tree. A base
update passes when its parents are the approved sha and the tip and its
tree is the recorded one. A head that changed content otherwise is still
held for a delta review. `land.py` passes `--merge-base` through `git
merge-base` with the old sha. The old sha must be in the local object
store, which the batch merge's fetch ensures.

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
  apply whatever the overlay and local bodies say follows a git update.
- Close the delivered issue with a handoff comment, drawn from the Dev
  record's "left undone" and the review record's "watch next". A PR into a
  non-default branch does not close its issue on GitHub's own.
- Close any umbrella issue whose sub-tasks have all landed, with a handoff.
- An issue that depended on this one may now be claimable; the next `run`
  pass picks it up.
- When a `run` invocation (`SKILL.md`, The quiet pass) has landed anything
  and `<gate_wave>` is set, run it once on the new tip before each
  quiet-pass report. It is judged as a delta: if it is
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
- When a parent lands, GitHub retargets a linked child itself, and rebases
  it unless its branch carries merges; `batch.py land` handles the rest.
  Outside it, an unlinked child (a fork arm, or a chain never linked) gets
  its base patched
  (`gh api -X PATCH repos/<repo>/pulls/<child> -f base=<integration_branch>`)
  and the new tip merged into it, so its diff shows only its own changes,
  then gets the round comment that `rules.md` (Branches) requires.
