---
name: agent-team
description: Runs a team of developer and reviewer agents over a GitHub issue pool -- plan briefs, develop, review to APPROVE, land squashed -- under standing rules and a per-project overlay. User-invoked: /agent-team plan|run|status|verdict|advise, run and status taking an optional scope, verdict the ruling of a held item's ruler, advise a read-only analysis of one held item and the ruling to make.
disable-model-invocation: true
---

# agent-team

You orchestrate. Developer agents own a task's change and its PR; reviewer
agents review each head until APPROVE; you land what is approved. GitHub is
the only task record -- briefs in issues, dev and review records in PRs,
handoffs in closing comments -- so any session can pick up where another
stopped. An item's ruler (`rules.md`, Escalations) rules on its
escalations, through the `need human` label and `verdict`, and on nothing
else; `advise` analyses one before the ruler rules.

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
   further until it loads clean; `status` continues on whatever resolved;
   `verdict` and `advise` stop (`verdict.md`, `advise.md`).
2. Read `rules.md`, the overlay body, and then the body of
   `.claude/agent-team.local.md` when that file exists (`overlay.md`). All
   bind you as much as any agent you dispatch; where the two bodies
   conflict, the local one wins.
3. In `plan` and `run`, create the `need human` label in `<repo>` if
   `gh label list` lacks it.
4. Note whether the `ponytail` and `ponytail-review` skills are installed. If
   not, say so once in your first report; developers and reviewers then skip
   them.

## Scope

`run` and `status` take an optional free-text argument naming issues,
labels and PRs. It has no fixed syntax: read it as the owner wrote it.
Resolve it again every pass, so an issue that gains a named label joins.

- **No argument** means the whole pool: every open issue in `<repo>`,
  restricted to `<task_label>` when set.
- **An in-scope issue belongs to this session** only when it has no
  assignee or its assignees include the current `gh` user (`gh api user`).
  One assigned to someone else leaves the scope unless the argument says to
  keep it. Sessions on one machine usually share a `gh` login, so assignees
  separate people and the scope separates sessions.
- **Concurrent sessions' scopes must not overlap**, and everything in scope
  is this session's to advance. Assignees keep two people apart; only the
  scope keeps one person's sessions apart, and overlapping scopes dispatch
  duplicate developers.
- **PRs follow issues.** A run acts only on PRs that deliver an in-scope
  issue (`rules.md`, Check delivery), plus PRs the argument names, which
  are not assignee-checked. This holds with no argument too: a PR that
  delivers no pool issue is not acted on.
- **A dependency outside the scope is another session's work**: never
  claimed or advanced, only waited for.

## status

Read-only; changes nothing on GitHub or disk. Report, within the scope:

- every open PR: its `pr_state.py` turn and holds;
- every open issue, classified as in `run`, step 1, with what blocks it;
- every `need human` item, the ruling it waits on, and its ruler
  (`python3 <skill-dir>/ruler.py N --repo <repo>`), or `no ruler: hand off
  first` when it has none.

**Done when** every open in-scope PR and issue appears exactly once, and
the first line says whether anything blocks.

## plan

Read `plan.md` and follow it.

## verdict

Read `verdict.md` and follow it.

## advise

Read `advise.md` and follow it.

## run

`run` keeps no state of its own. Each **pass** rereads GitHub and advances
every item by at most one step, so a run can stop at any point -- interrupt,
context compaction, a new session -- and the next `run` resumes from GitHub
alone. Do not wrap `run` in `/loop`: it schedules itself (The check).

### One pass

Every pass starts by replacing the check (The check, below).

1. **Read the pool**: the open issues in scope (Scope). For each, read its
   comments and its `Depends on #N` lines and check delivery (`rules.md`).
   Classify it:
   - **held** -- `need human` on it;
   - **in progress** -- a `Claimed` comment, or an open PR that delivers it;
   - **needs a brief** -- the brief lacks a file set, exit criteria, a
     named result or an effort estimate, or estimates above `<split_loc>`
     lines without being decomposed (`plan.md`). Never write the brief here:
     that is `plan`'s job, and it ends in owner review;
   - **blocked** -- a dependency is still open; a dependency on a missing
     issue, or a cycle, is a finding to report;
   - **claimable** -- none of the above.
2. **Land.** For every open PR in scope, run `python3 <skill-dir>/pr_state.py
   <pr> --repo <repo>`. Land each PR whose turn is `land` and whose base is
   `<integration_branch>`, per `land.md`; a stacked child waits for the PR
   below it.
3. **Review.** Dispatch a reviewer (below) for each PR whose turn is
   `reviewer` and that has no agent of yours running on it.
4. **Develop.** Dispatch the PR's developer for each PR whose turn is
   `developer` and that has no agent of yours running on it. Dispatch a
   developer, told the issue is already claimed, for each in-progress
   issue with a `Claimed` comment, no open delivering PR and no agent of
   yours running on it: a claim whose session ended is otherwise never
   advanced and holds a slot forever. Then, while fewer than `<max_tasks>`
   tasks are in flight, claim the next claimable issue (`develop.md`, Read
   and claim) and dispatch a developer for it. Claim before dispatching,
   so a concurrent session cannot take the same issue.

   A task is **in flight** when its issue is in scope, in progress, and
   has no `need human`. A PR under `hold landing` and a stacked child
   waiting for its parent count; a held task does not.

**An escalation holds its item, never the run.** Post the ruling request
with `need human` (`rules.md`, Escalations), name it in your next report,
and continue the pass. Never block a run on an interactive question: a
`run` never waits on the owner while unheld work remains.

When a pass lands nothing and dispatches nothing, wait for a running agent to
finish, then pass again.

### The quiet pass

A **quiet pass** lands nothing, dispatches nothing, and finds no agent of
yours running. It ends the invocation: one `/agent-team run` prompt, typed
by the owner or fired by a check, so the run stays stateless across checks.

1. If this invocation landed anything, run `<gate_wave>` (`land.md`, After
   landing).
2. If any in-scope issue is open, whatever its class -- held and needing a
   brief included -- give an interim report; the check wakes the next pass.
   Otherwise give the final report -- what landed, what is held and on
   which hold, what waits on a ruling -- delete the check (`CronList`, then
   `CronDelete` each ID whose prompt matches), and end.

The interim report is a full report only when an issue's class or what it
waits on changed since this session's last report, or that report is not
in context; otherwise it is one line, `No change; next check ~:MM.` A full
interim report follows `rules.md` (Talking to the owner): whether anything
blocks; each open in-scope issue, its class and what it waits on; when the
next check fires. Both reports split what waits on a ruling by
each held item's ruler (`ruler.py`): "waits on me" when it is the current
`gh` user, "waits on @x" when it is another login, and `no ruler: hand off
first` when it has none.

**Done when** a quiet pass finds no open in-scope issue and gives the final
report.

### The check

The check is a recurring `CronCreate` at `7,22,37,52 * * * *` whose prompt
is `/agent-team run <argument>`, the original argument verbatim. It is the
run's only wake signal: a ruler on another account cannot reach this
session, and GitHub is what both share. Every check runs a full pass, with
no cheaper pre-check.

At the start of every pass, replace it: `CronList` and note the IDs whose
prompt matches, `CronCreate` the new one, then `CronDelete` the noted IDs.
Create before delete, so a check always exists. Replacing it every pass
keeps a recurring job from reaching its 7-day expiry, whose final fire
would otherwise see itself pending and recreate nothing. A check lives
only in the session that scheduled it and fires only while that session is
idle: closing the session ends the wait, and a busy session delays it.

### Dispatching

One background agent per role per task, so at most `2 x <max_tasks>` agents
run. Review throughput, not the DAG, is what caps concurrency. Give each
agent no prose of your own about how to work; hand it:

- as the prompt's first line, the run-location constraints the project's
  local instructions state (`CLAUDE.local.md`, say), quoted verbatim: an
  agent runs commands before it reads its docs. Send any change to them to
  every running agent at once;
- its role doc: `<skill-dir>/develop.md` or `<skill-dir>/review.md`, which
  points it at `rules.md`;
- the issue number (developer) or PR number (reviewer);
- the overlay keys as JSON, without `conversation_language`: it governs
  only what you say to the owner, and an agent's report goes to you;
- the overlay body, then the local body when there is one, last, and
  winning where the two conflict;
- `<skill-dir>`, and that `<design_entry>` is read first.

The brief is written close to a prompt for exactly this reason: a prompt
assembled from the issue at launch cannot drift from it, where a stored
prompt template would.

An agent that ends without reaching its doc's completion criterion is a
finding: read what it reported, and either dispatch again with that context
or escalate.
