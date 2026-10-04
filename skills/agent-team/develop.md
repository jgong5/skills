# Developer

You own one task: its change, its PR, and every PR update until the verdict
is APPROVE. You were given an issue number, the overlay keys and body, and
this skill's directory.

When the task already has a PR, you are answering its last verdict: read as
in step 1, reuse `<worktree_root>/<n>` (or recreate it from the PR branch),
and continue from step 3.

## 1. Read and claim

Read `<design_entry>` first, then `rules.md`, the issue's body and comments,
and the handoff comments of the issues it depends on. Check delivery
(`rules.md`). Unless the orchestrator says it already claimed the issue,
claim it: assign it (`gh issue edit <n> --add-assignee @me`) and comment
`Claimed: branch task-<n>.` It names the branch only: when the orchestrator
claims, no worktree exists yet, so a path would be false.

## 2. Set up the tree

Fetch `<remote>`, then `git worktree add <worktree_root>/<n> -b task-<n>
<remote>/<integration_branch>` -- or, to stack on an unlanded parent's PR,
from the parent's head (`land.md`, Stacking). Run `<import_check>` there when
it is set. Apply whatever the overlay body says a fresh tree needs.

## 3. Build

Work under the `ponytail` skill at level `full` (`/ponytail full`) when it is
installed. Stay inside the brief's file set; record any change outside it
under Decided in the Dev record. Track your non-test lines against the brief's
code estimate; at the overrun `rules.md` (Escalations) sets, stop and
escalate.

## 4. Pass the gates

1. **`<gate_task>` passes at your head, with the project's existing tests
   unmodified.** Needing to edit an existing test means the change altered
   existing behaviour; justify that on its own terms in the Dev record, never
   by quietly adjusting the test.
2. **New tests for what the task added**, in `<new_tests_dir>` when set, in
   the project's style. **They must exercise something the PR did not itself
   add**: a new module plus tests for that module, imported by nothing else,
   passes every gate and demonstrates nothing.
3. **The brief's named result**, shown as stated -- not a different result
   that happened to pass.

**A check counts only once someone has seen it fire.** Before claiming a test
holds a fix, reinstate the pre-fix code (`git show <base>:<path>`, line count
preserved, nothing else changed), run the test, and record the red: both
pass/fail counts, the failing test id and its assertion. Then restore the
fix.

## 5. Open or update the PR

The PR targets `<integration_branch>` (or the parent's branch when stacked),
its title says what the task does, and its body follows `gh-prose`'s PR body
shape and names the issue (`Closes #<n>`). Rewrite the body in place each
round so it describes the current state. After every push, comment
`Round <k> pushed <sha>.` with what changed since the last round, one line
per answered finding: fixed in which commit, or why not, with evidence.

Answer findings with new commits only (`rules.md`, Branches). Run every
GitHub text through `gh-prose`'s lint before posting.

**Done when** the PR is open, `<gate_task>` is green at its head, the body is
current, and the latest round comment names that head. Then stop: the
orchestrator sends a reviewer.
