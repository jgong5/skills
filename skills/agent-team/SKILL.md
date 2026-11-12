---
name: agent-team
description: Runs a team of developer and reviewer agents over a GitHub issue pool -- plan briefs, develop, review to APPROVE, land squashed -- under standing rules and a per-project overlay, or in auto mode takes a requirement to an accepted feature. User-invoked: /agent-team auto|plan|run|status|verdict|advise, auto taking a requirement (a prompt, #issue or document path), run and status taking an optional scope, verdict the ruling of a held item's ruler, advise a read-only analysis of one held item and the ruling to make.
disable-model-invocation: true
---

# agent-team

You orchestrate. Developer agents own a task's change and its PR; reviewer
agents review each head until APPROVE; you land what is approved. GitHub is
the only task record -- briefs in issues, dev and review records in PRs,
handoffs in closing comments -- so any session can pick up where another
stopped. An item's ruler (`rules.md`, Escalations) rules on its
escalations, through the `agent-team/need-human` label and `verdict`, and
on nothing else; `advise` analyses one before the ruler rules.

In auto mode the owner states a requirement and confirms it once (`auto`);
agents then also design, plan, check acceptance and rule on how to build,
through `agent-team/ruling` and a ruling agent. The owner is asked only
about what to build, an action outside the repository, and acceptance.

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

1. From the repository, run `python3 <skill-dir>/overlay.py`. When a
   `run`'s argument names an auto umbrella (Scope), read the umbrella,
   fetch `<remote>` and run it again with `--ref`: the ref its body's
   `Overlay: <ref> (#P)` line names while #P is open, else
   `<remote>/<branch>` for its `Integration branch: <branch>`. Pass the
   same `--ref` to every `land.py` and `batch.py` call (`land.md`), and
   reread both lines every pass, so the run switches when #P lands. Exit 0
   prints
   the resolved keys as JSON, and any warning, such as a deprecated key, on
   stderr: pass each warning to the owner in your first report. Exit 1
   prints every problem: in `plan` and `run`, read `overlay.md` and draft
   the overlay with the owner, and go no further until it loads clean;
   `status` continues on whatever resolved; `verdict` and `advise` stop
   (`verdict.md`, `advise.md`).
2. Read `rules.md`, the overlay body, and then the body of
   `.claude/agent-team.local.md` when that file exists (`overlay.md`). All
   bind you as much as any agent you dispatch; where the two bodies
   conflict, the local one wins.
3. In `plan` and `run`, read `gh label list`. Each old label present
   without its new name -- `need human` (`agent-team/need-human`),
   `hold landing` (`agent-team/hold-landing`), `land as merge`
   (`agent-team/land-as-merge`) -- is renamed with `gh label edit <old>
   --name <new>`, which keeps it on every item that carries it; say so in
   your first report. Then create `agent-team/need-human` if it is still
   missing, and, when the argument names an auto umbrella, `agent-team/ruling`,
   `agent-team/spike`, `agent-team/backlog` and `agent-team/land-as-merge`.
   The scripts read the old names too, for one version.
4. Note whether the `ponytail` and `ponytail-review` skills are installed. If
   not, say so once in your first report; developers and reviewers then skip
   them.

## Scope

`run` and `status` take an optional free-text argument naming issues,
labels and PRs. It has no fixed syntax: read it as the owner wrote it.
Resolve it again every pass, so an issue that gains a named label joins.

- **No argument** means the whole pool: every open issue in `<repo>`,
  restricted to `<task_label>` when set, except auto umbrellas and their
  issues, which belong to the umbrella's own run.
- **Membership and mode.** An issue is under umbrella #U when its body has
  a `Part of #U` line, read like `Depends on #N`, and is an **auto item**
  when #U carries `agent-team/auto`; every other item is manual. Read both
  from GitHub every pass: removing the label returns the umbrella's issues
  to the manual flow. Manual and auto items mix in one scope; the rules
  apply per item.
- **An argument naming an auto umbrella** brings in every issue under it
  and the open PR its `Overlay:` line names. Naming an auto item from any
  other run is the owner's call, under the rule against overlapping scopes.
- **The umbrella is never a task**: it is never classified, claimed or
  briefed. The run reads it for membership, its integration branch,
  acceptance and vetoes (One pass, step 5).
- **One run serves one integration branch**, the one Step 0 loaded. An
  auto item whose umbrella names another is a finding: report it and skip
  it.
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
- every auto umbrella, with what `run`, step 5, would dispatch for it;
- every `agent-team/need-human` item, the ruling it waits on, and its ruler
  (`python3 <skill-dir>/ruler.py N --repo <repo>`), or `no ruler: hand off
  first` when it has none; every `agent-team/ruling` item waits on a
  ruling agent.

**Done when** every open in-scope PR and issue appears exactly once, and
the first line says whether anything blocks.

## auto

Read `auto.md` and follow it.

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

Every pass starts by replacing the check (The check, below), then stops
(`TaskStop`) each agent of yours whose final report has arrived: a
background task it armed and never stopped keeps it live, and a live agent
can hold a headless check, as seen on the SDK. An agent counts as running
only until its final report.

1. **Read the pool**: the open issues in scope (Scope). For each, read its
   comments and its `Depends on #N` lines and check delivery (`rules.md`).
   Classify it:
   - **held** -- `agent-team/need-human` or `agent-team/ruling` on it;
   - **backlog** -- `agent-team/backlog` on it: never claimed, until the
     owner removes the label;
   - **in progress** -- an open PR that delivers it, or a `Claimed`
     comment and every dependency closed: a dependency added after the
     claim, such as a designer's spike, blocks it;
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
   is not held. A PR under `agent-team/hold-landing` and a stacked child
   waiting for its parent count; a held task does not.

5. **Auto.** Dispatch, each when no agent of yours runs on its item:
   - a ruling agent for each item `agent-team/ruling` holds;
   - a planner for each unheld in-scope auto umbrella whose
     `agent-team/design` issues are all closed, when its thread has no plan
     record (a comment opening `Ready: plan published`) since the last of
     them closed or since its latest `Ruling: overturn #N:`. That is the
     owner's veto: the planner files its follow-ups under the umbrella,
     and a rollback is new commits, never a force-push. A veto on any
     other item is never read;
   - an acceptor for each unheld in-scope auto umbrella whose issues are
     all closed and that needs no planner.

**An escalation holds its item, never the run.** Post the ruling request
with the item's label (`rules.md`, Escalations), name it in your
next report, and continue the pass. Never block a run on an interactive question: a
`run` never waits on the owner while unheld work remains.

Every pass ends by stopping its timer if it still runs (`TaskStop`). If
agents of yours are still running, whatever the pass landed or dispatched,
start a fresh timer, `sleep 900` through Bash `run_in_background`, and wait:
the first agent to finish or the timer's exit runs the next full pass. The
timer wakes the run while its agents run, because a headless session's
check may not fire then (The check). Whichever of check and timer woke the
pass, the fresh timer restarts the 15 minutes and can hold a headless check.

### The quiet pass

A **quiet pass** lands nothing, dispatches nothing, and finds no agent of
yours running. It ends the invocation: one `/agent-team run` prompt, typed
by the owner or fired by a check, so the run stays stateless across checks.

1. If this invocation landed anything, run `<gate_post_land>` (`land.md`,
   After landing).
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
is `/agent-team run <argument>`, the original argument verbatim. It wakes
the run when nothing of its own will: a ruler on another account cannot
reach this session, and GitHub is what both share. Every check runs a full
pass, with no cheaper pre-check.

At the start of every pass, replace it: `CronList` and note the IDs whose
prompt matches, `CronCreate` the new one, then `CronDelete` the noted IDs.
Create before delete, so a check always exists. Replacing it every pass
keeps a recurring job from reaching its 7-day expiry, whose final fire
would otherwise see itself pending and recreate nothing. A check lives
only in the session that scheduled it; closing the session ends the wait.
When it fires depends on the session kind. A headless session can count
a live background task, agent or Bash, the timer included, as busy and not
fire its check while one runs: seen on the SDK, while `claude -p` with
`stream-json` has fired a check past a live Bash task. An interactive
session fires it between turns, so a busy turn delays it.

### Dispatching

One background agent per role per item, so at most `2 x <max_tasks>`
developers and reviewers run, beside planners, acceptors and ruling agents.
Review throughput, not the DAG, is what caps concurrency. Give each
agent no prose of your own about how to work; hand it:

- as the prompt's first line, the run-location constraints the project's
  local instructions state (`CLAUDE.local.md`, say), quoted verbatim: an
  agent runs commands before it reads its docs. Send any change to them to
  every running agent at once;
- its role doc, which points it at `rules.md`. Developer and reviewer
  docs go by the issue's label, a PR taking the issue's it delivers:
  `agent-team/design` gets `design.md` to develop and `design-review.md`
  to review, `agent-team/spike` gets `spike.md` and `review.md`, any other
  issue `develop.md` and `review.md`. A planner gets `plan.md`, a ruling agent
  `ruling.md`, an acceptor `accept.md`, all under `<skill-dir>`;
- the issue number (developer), PR number (reviewer), umbrella (planner,
  acceptor) or held item (ruling agent), and its mode, `manual` or `auto
  under #U`, which decides the label an escalation takes;
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
