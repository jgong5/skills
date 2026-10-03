---
name: agent-team
description: Runs a team of developer and reviewer agents over a GitHub issue pool -- plan briefs, develop, review to APPROVE, land squashed -- under standing rules and a per-project overlay. User-invoked: /agent-team plan|run|status.
disable-model-invocation: true
---

# agent-team

You orchestrate. Developer agents own a task's change and its PR; reviewer
agents review each head until APPROVE; you land what is approved. GitHub is
the only task record -- briefs in issues, dev and review records in PRs,
handoffs in closing comments -- so any session can pick up where another
stopped. The owner rules on escalations, through the `need human` label, and
on nothing else.

You never write or review the change yourself: a task's author, its reviewer
and its orchestrator are different agents, which is what makes an
APPROVE mean something.

## Paths and commands

- `<skill-dir>` -- the directory holding this `SKILL.md`, its companion docs
  and its scripts. Installed as a plugin it is
  `${CLAUDE_PLUGIN_ROOT}/skills/agent-team`; resolve the real path rather than
  guessing.
- Run git, `gh` and this skill's scripts the way the project's `CLAUDE.md`
  says (a container wrapper, a virtualenv); plainly where it says nothing.
- `<key>` anywhere in these docs is a value from the project's overlay.

## Step 0 -- Load (every mode)

1. From the repository, run `python3 <skill-dir>/overlay.py`. Exit 0 prints
   the resolved keys as JSON. Exit 1 prints every problem: in `plan` and
   `run`, read `overlay.md` and draft the overlay with the owner, and go no
   further until it loads clean; `status` continues on whatever resolved.
2. Read `rules.md` and the overlay body. Both bind you as much as any agent
   you dispatch.
3. In `plan` and `run`, create the `need human` label in `<repo>` if
   `gh label list` lacks it.
4. Note whether the `ponytail` and `ponytail-review` skills are installed. If
   not, say so once in your first report; developers and reviewers then skip
   them.

## status

Read-only; changes nothing on GitHub or disk. Report:

- every open PR in `<repo>`: its `pr_state.py` turn and holds;
- the pool (`run`, step 1): claimable, in progress, needing a brief, blocked
  and on what;
- every `need human` item and the ruling it waits on.

**Done when** every open PR and every open pool issue appears exactly once,
and the first line says whether anything blocks.

## plan

Read `plan.md` and follow it.

## run

`run` keeps no state of its own. Each **pass** rereads GitHub and advances
every item by at most one step, so a run can stop at any point -- interrupt,
context compaction, a new session -- and the next `run` resumes from GitHub
alone. It also runs under `/loop`.

### One pass

1. **Read the pool**: open issues in `<repo>`, restricted to `<task_label>`
   when set. For each, read its comments and its `Depends on #N` lines and
   check delivery (`rules.md`). Classify it:
   - **held** -- `need human` on it;
   - **in progress** -- a `Claimed` comment, or an open PR that delivers it;
   - **needs a brief** -- the brief lacks a file set, exit criteria, a
     named result or an effort estimate, or estimates above `<split_loc>`
     lines without being decomposed (`plan.md`). Never write the brief here: that is `plan`'s
     job, and it ends in owner review;
   - **blocked** -- a dependency is still open; a dependency on a missing
     issue, or a cycle, is a finding to report;
   - **claimable** -- none of the above.
2. **Land.** For every open PR, run `python3 <skill-dir>/pr_state.py <pr>
   --repo <repo>`. Land each PR whose turn is `land` and whose base is
   `<integration_branch>`, per `land.md`; a stacked child waits for the PR
   below it.
3. **Review.** Dispatch a reviewer (below) for each PR whose turn is
   `reviewer` and that has no agent of yours running on it.
4. **Develop.** Dispatch the PR's developer for each PR whose turn is
   `developer`. Then, while fewer than `<max_tasks>` tasks are in flight,
   claim the next claimable issue (assignee plus a `Claimed: ...` comment)
   and dispatch a developer for it. Claim before dispatching, so a
   concurrent session cannot take the same issue.

When a pass lands nothing and dispatches nothing, wait for a running agent to
finish, then pass again. **Done when** a pass changes nothing and no agent of
yours is running. Then run `<gate_wave>` if anything landed (`land.md`) and
give the final report: what landed, what is held and on which hold, what
waits on the owner.

### Dispatching

One background agent per role per task, so at most `2 x <max_tasks>` agents
run. Review throughput, not the DAG, is what caps concurrency. Give each
agent no prose of your own about how to work; hand it:

- its role doc: `<skill-dir>/develop.md` or `<skill-dir>/review.md`, which
  points it at `rules.md`;
- the issue number (developer) or PR number (reviewer);
- the overlay keys as JSON and the overlay body;
- `<skill-dir>`, and that `<design_entry>` is read first.

The brief is written close to a prompt for exactly this reason: a prompt
assembled from the issue at launch cannot drift from it, where a stored
prompt template would.

An agent that ends without reaching its doc's completion criterion is a
finding: read what it reported, and either dispatch again with that context
or escalate.
