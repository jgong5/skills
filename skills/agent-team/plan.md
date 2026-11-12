# plan: turn intent into claimable briefs

Input is one of: a design document, a goal stated in a sentence, or `#N ...`
existing issues to brief or decompose. Output is a set of issues in `<repo>`
whose briefs make each one claimable, linked into a DAG by `Depends on #N`
lines. There is no separate DAG document: the issues are the DAG, and `run`
rebuilds it from them on every pass.

## 1. Read

Read `<design_entry>`, the input, and the code it touches. For `#N` input,
read each issue's comments and check delivery (`rules.md`) first. Read the
open issues in the pool, so you extend the existing DAG instead of
duplicating it.

**Done when** you can name, for every piece of work the input implies, the
module it lands in and the interfaces it implements and consumes.

## 2. Cut

- One task is one module plus its tests. Two tasks that must edit the same
  file are one task, or are ordered by `Depends on`.
- **Decompose a task estimated above `<split_loc>` lines, tests included, or
  with three or more deliverables** into sub-tasks, each its own issue with
  its own brief, before anyone claims it. Estimate effort in lines
  (`rules.md`, Escalations, says how they are counted): lines are what a
  reviewer reads and what a developer can check against.
  Wall-clock appears only for machine time with a measured basis.
- An umbrella issue that only groups sub-tasks still carries a named result,
  or names the sub-task that carries it.

**Done when** every task has a file set it can name. A brief that cannot
name its file set is not claimable, so a task that cannot name one is not
cut yet.

## 3. Write each brief

Follow `gh-prose` (kind `brief`). Every brief has:

- **Implements / Consumes** -- the interfaces, by path and symbol.
- **File set** -- the files it creates or edits.
- **Exit criteria** -- what is true when it is done, checkably.
- **Named result** -- the one result the task must show, chosen now. A
  developer choosing it afterwards can always find one that passed; that is
  the case this rule forbids.
- **Effort** -- the weighted code and test totals (`rules.md`, Escalations),
  estimated separately, each with its added, moved and deleted counts.
- **Depends on** -- one `Depends on #N` line per predecessor, and links to
  their issues. Omit the lines for a root task.

Each brief also says which existing behaviour its new tests will exercise:
a new module tested only by its own tests, imported by nothing else, passes
every gate and demonstrates nothing (`develop.md`, gate 2).

## 4. Owner review, then publish

Show the owner the DAG (each task: title, effort, `Depends on`) and the
briefs, and wait; in auto mode, Auto mode (below) replaces this review.
Creating and editing issues publishes, so nothing reaches GitHub before
the owner approves. Then create or edit the issues, applying
`<task_label>` when it is set, and fill in the `#N` numbers in the
`Depends on` lines as the dependency issues get them. Create parents before
children so every number exists when it is cited. Editing the body of an
issue with open delivering PRs (`rules.md`, Check delivery) posts
`Brief updated: <parts>. <link to the issue>` on each, linted as
`--kind comment`.

**Done when** every approved task is an issue whose brief has every part step 3
lists and whose `Depends on` lines name existing issues, and you have told the
owner which tasks are claimable now.

## Auto mode

Nobody waits for the owner here, so a plan review takes the place of step
4's owner review. You are in auto mode when `run` dispatched you for an
auto umbrella #U (`SKILL.md`, One pass, step 5), or when a ruling agent
carries out a split (`verdict.md`, step 4) on an issue under one.

1. **Input.** For #U: its requirement document, the design documents its
   `agent-team/design` issues landed, and each `Ruling: overturn #N:` in
   its thread since your last plan record there. A veto that overturns a
   design decision gets a `Design update: <feature>` issue labeled
   `agent-team/design`, and the re-plan waits for it to land. For a split:
   `#N`, as step 1 reads it.
2. **Draft.** Steps 1-3 as written, every brief opening with `Part of
   #U`, written to `<scratch>/plan-<U>.md`. Publish nothing: a session
   that dies now loses only the draft, and the next pass plans again.
3. **Plan review.** Dispatch a fresh reviewer agent with this doc, the
   input and the draft's path, and none of your reasoning. It checks the
   draft against steps 2 and 3, and that every acceptance item is covered
   by some task's exit criteria or named result, and writes to scratch its
   findings, `<problem>. <fix>.`, each marked blocking or not. Revise and
   have it review again, two reviews at most. A blocking finding left
   after the second: post a ruling request (`gh-prose`) on the item you
   plan for, #U or the issue split, apply `agent-team/ruling`, and stop.
4. **Publish** as step 4 does once approved. Then post the review record
   on the item you plan for, linted as `--kind comment`, its first line
   `Ready: plan published: #a, #b.`, its `Checked:` line the acceptance
   coverage, and both reviews in `<details>`. On #U, `run` reads that line
   as the plan done.

**Done when** every task of the passing draft is an issue as step 4 says
and the record is posted, or the ruling request is.
