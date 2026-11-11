# Spike

You answer one design question with a measurement. Its script is reviewed
and reproduced like code but never lands: the PR is closed, not merged, and
the result lives in the PR and the issue. You were given an issue labeled
`agent-team/spike`, the overlay keys and body, and this skill's directory.

## 1. Read, claim, set up

As `develop.md` steps 1 and 2: read, claim unless the orchestrator already
did, and work in `<worktree_root>/<n>` on `task-<n>`. The brief states the
question and what figure would settle it.

## 2. Measure

Write the script that takes the measurement and commit it in a new `spike/`
directory at the root, or wherever else nothing the project runs (a test
collector, say) picks it up. The branch holds nothing else, so its head
measures the project as of its base, and since it never lands, the script
is not a file in the tree (`rules.md`, The task record). Run the script at
that head, repeating the measurement, and state the spread you saw, so a
reviewer can tell a reproduction from a different result. Track lines as
`develop.md` step 3; `<gate_task>` and the new-test gate do not apply.

## 3. Open the PR

Open it as `develop.md` step 5 does, with `--label agent-team/spike`: the
label is what makes `land.py` close the PR instead of merging the script
into the tree. The PR body (`gh-prose`'s shape) is its Dev record; under
`## Named result` it states:

- `Result:` the answer to the brief's question, in one line;
- the command, run from the repository root, exactly as the reviewer runs
  it;
- the head sha measured at (measure again after a commit that changes the
  script), and the machine or environment it ran in, which is where a
  reviewer reproduces it;
- the spread a reproduction must fall within.

The command's output from every run goes verbatim in its Evidence
`<details>`.

Post the round comment as `develop.md` step 5 does, and answer findings the
same way.

**Done when** the PR is open with `agent-team/spike`, its body states all
of the above, and the latest round comment names its head. The lander
then closes it and writes the issue's handoff (`land.md`, Land one PR).
