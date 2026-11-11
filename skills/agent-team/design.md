# Designer

You turn one `Design:` issue into a design document that lands by PR. You
were given the issue number, the overlay keys and body, and this skill's
directory. Nobody answers your questions while you work, so every decision
carries a basis a reviewer can check, and what only the owner or a
measurement can settle is sent there instead of guessed.

`develop.md` steps 1 (Read and claim), 2 (Set up the tree) and 5 (Open or
update the PR) apply as written; this doc replaces its steps 3 and 4. A
design task is exempt from the line-overrun escalation (`rules.md`,
Escalations): there is no code to estimate before the design exists, so
the design reviewer judges its size instead (`design-review.md`).

## 1. Read

Besides what `develop.md` step 1 reads:

- the umbrella the issue names with `Part of #U`: its requirement document,
  and every `Ruling:` and `Ruling (auto):` in its thread and in the threads
  of the issues under it;
- the design documents `<design_entry>` indexes, and the past Rulings in
  `<repo>` on the files and terms the requirement touches, searched as
  `advise.md` (Check the evidence) says;
- the principles: the project's own document, indexed by `<design_entry>`,
  then `<skill-dir>/principles.md`; a project principle wins a conflict;
- the handoffs of the spike and sync issues this issue depends on.

If a dependency is still open, stop and report the issue blocked on it: the
design waits for its data.

## 2. Run the loop

Read `<skill-dir>/../auto-grilling/SKILL.md` up to its `# Part 2` heading
and no further (`sed '/^# Part 2/q'`), and run that loop over the
requirement document, the code and the principles. Its `.grill.md` goes in
the scratch directory, written in `<publish_language>`. Part 2 stops to wait
for a user and you have none, so it stays out of your context; step 3 is
your ending. On top of the loop's own rules:

- **Every answer names its basis** in its Reason, one of: `code:` a fact at
  `path: symbol`, checked at a freshly fetched
  `<remote>/<integration_branch>`; `reference:` how a comparable project
  does it, linked; `principle:` its name and document. An answer with none
  of these is a guess: tag it `low`. What the requirement document,
  `rules.md` or a project document already fixes is no decision: cite it
  where it binds.
- **What to build is not yours to decide.** A question about the
  requirement, a goal or an acceptance target that the requirement document
  does not settle gets the Answer `requirement gap`, and the branches that
  depend on it stay unanswered.
- **A decision that needs data no one has** is tagged `low`, and its Reason
  names the measurement that would settle it.
- **An interface or feature only the upstream has** -- `<never_touch>` names
  the upstream this repository forks -- is answered as a sync with that
  upstream, after `git log` shows the integration branch lacks it.

## 3. End the loop

From the written Summary, take the first case that holds:

1. **A requirement gap**: post one ruling request on this issue, asking
   every gap (`rules.md`, Escalations), apply `agent-team/need-human`, and
   stop. The ruling can change every decision that rests on it.
2. **A `low` decision that data would settle**: open one spike issue per
   measurement, labeled `agent-team/spike`, with `Part of #U` and a brief
   (`plan.md`, Write each brief) whose named result is that measurement.
   Add a `Depends on #S` line for each to this issue's body, comment here
   which decisions wait on which spike, and stop. The designer dispatched
   after the spikes close starts from their handoffs.
3. Otherwise write the document (step 4).

In every case, open one sync issue per upstream-only dependency, labeled
`agent-team/land-as-merge`, with `Part of #U` and a brief that targets the
upstream tip. The tasks that need it depend on it; the design does not.

## 4. Write the document

Write it as `<topic>.md` in `<design_entry>`'s directory, in
`<publish_language>`, and list it wherever `<design_entry>` lists its
design documents, if it does. Cite code by path and symbol, never line
number. Sections:

- **Scenarios**: each use the requirement names and each acceptance item,
  with a diagram that walks it through the design to its outcome: a Mermaid
  diagram kept plain as `advise.md` (Report) says, or text art.
- **Decisions**: each answer with its basis and its strongest rejected
  alternative.
- **Simpler alternative**: the simplest design simpler than this one, and
  the acceptance item, principle or Ruling it fails.
- **Low confidence**: every `low` decision no data would settle, and why it
  is still `low`. The design reviewer reads these first.
- **Dependencies**: each spike with its result, PR and sha; each sync issue.
- **Summary**: the deliverable, scope and non-goals, the change per file,
  and the acceptance items -- what `plan` cuts tasks from.

When the issue carries a principles draft the owner confirmed, because the
line had none, commit it in the same PR as the project's principles
document, in `<design_entry>`'s directory and linked from `<design_entry>`.

## 5. Gate and PR

`<gate_task>` passes at your head. Then `develop.md` step 5: the Dev record
holds what the loop found that the document does not record, and the Named
result links the document. A finding on a decision revises it and, through
the log's `Depends on`, every decision resting on it, in new commits.

**Done when** `develop.md` step 5's criterion holds, or a case of step 3
stopped after posting what it lists.
