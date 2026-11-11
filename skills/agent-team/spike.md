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

Write the script that takes the measurement and commit it where nothing the
project runs picks it up (a test collector, say); the branch holds nothing
else, so its head measures the project as of its base. Run it at that head,
more than once, and state the spread you saw, so a reviewer can tell a
reproduction from a different result. Track lines as `develop.md` step 3;
`<gate_task>` and the new-test gate do not apply.

## 3. Open the PR

Open it as `develop.md` step 5 does, with `--label agent-team/spike`: the
label is what makes `land.py` close the PR instead of merging the script
into the tree. Its Dev record states:

- `Result:` the answer to the brief's question, in one line;
- the command, run from the repository root, exactly as the reviewer runs
  it;
- its output, verbatim, from every run;
- the head sha measured at (measure again after a commit that changes the
  script), and the machine or environment it ran in;
- the spread a reproduction must fall within.

Post the round comment as `develop.md` step 5 does, and answer findings the
same way.

**Done when** the PR is open with `agent-team/spike`, its Dev record states
all of the above, and the latest round comment names its head. The lander
then closes it and writes the issue's handoff (`land.md`, Land one PR).
