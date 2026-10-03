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
  its own brief, before anyone claims it. Estimate effort in lines of code:
  lines are what a reviewer reads and what a developer can check against.
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
- **Effort** -- an estimate in lines, tests included.
- **Depends on** -- one `Depends on #N` line per predecessor, and links to
  their issues. Omit the lines for a root task.

Each brief also says which existing behaviour its new tests will exercise:
a new module tested only by its own tests, imported by nothing else, passes
every gate and demonstrates nothing (`develop.md`, gate 2).

## 4. Owner review, then publish

Show the owner the DAG (each task: title, effort, `Depends on`) and the
briefs, and wait. Creating and editing issues publishes, so nothing reaches
GitHub before the owner approves. Then create or edit the issues, applying
`<task_label>` when it is set, and fill in the `#N` numbers in the
`Depends on` lines as the dependency issues get them. Create parents before
children so every number exists when it is cited.

**Done when** every approved task is an issue whose brief has every part step 3
lists and whose `Depends on` lines name existing issues, and you have told the
owner which tasks are claimable now.
