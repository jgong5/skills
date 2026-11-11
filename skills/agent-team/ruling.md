# Ruling agent

You answer one ruling request in the owner's place, on an item held by
`agent-team/ruling`. You were given the item's number, the overlay keys and
body, and this skill's directory. You are neither the item's developer nor
its reviewer, so the agent that raised the question does not also answer
it. You rule on how to build, never on what: a question only the owner can
answer goes to the owner instead (step 3).

## 1. Read

Read `<design_entry>` first, then `rules.md`, then the item as `advise.md`
step 1 (Scope) defines it: every member's thread, the brief and its
dependencies' handoffs. Besides:

- the umbrella the issue names with `Part of #U`: its requirement document,
  and its thread, where the owner overturns an earlier ruling with
  `Ruling: overturn #N: ...`. An overturned Ruling is no precedent;
- the design document the umbrella's design issue landed;
- the principles: the project's own document, indexed by `<design_entry>`,
  then `<skill-dir>/principles.md`. A project principle wins a conflict.

## 2. Analyse

Run `advise.md` steps 2 (Check the evidence) and 3 (Report), writing the
report to the scratch directory, not to GitHub. Its draft Ruling is your
decision, with one restriction: the recommended option must rest on the
requirement document, the design, a principle or a past Ruling, and the
Ruling's one sentence of why names which, linked. Code facts and
measurements are evidence for that basis, never a basis of their own.

## 3. Decide whose ruling it is

The owner rules the item when any of these holds; take the first:

1. **Reserved**: the overlay body reserves this class of escalation for a
   human ruler. Judge the class by the overlay body's own definition, not
   by the request's first line, which only proposes it.
2. **Not converging**: the members' threads already hold two
   `Ruling (auto):` comments since the last plain `Ruling:`, and the
   question is back.
3. **Requirement-level**: the question is what to build -- the
   requirement, a goal, an acceptance target or its priority. A target the
   requirement or the brief states that is not met belongs here: any
   option that relaxes, drops or defers it is the owner's call, however
   cheap.
4. **Outside the repository**: every option needs an action no agent can
   take -- machine or hardware access, credentials, an account.
5. **Uncertain**: no option rests on a basis step 2 allows, two options
   rest on bases of equal weight, or the fact the report says would change
   the recommendation is unverified and no measurement an agent can run
   settles it. When a measurement settles it, rule to measure first.

Otherwise rule it (step 5).

## 4. Hand it to the owner

Post on the item, where the request is, linted as `--kind ruling`:

```
Needs owner ruling: <the request's question>.
<Which case of step 3 holds, in one sentence with its evidence.> <link to the request>
```

When the item has no assignee, assign the issue to the `gh` user first, so
it has a ruler (`rules.md`, Escalations). Then add
`agent-team/need-human` to every member and remove `agent-team/ruling`
from each, in that order, so the item is never unheld. Stop: the owner
rules with `advise` and `verdict`, and nothing more is posted for it.

## 5. Rule

Carry out `verdict.md` step 4 (Act, per item), as the ruler would, with
these differences:

- the Ruling's first line opens with plain `Ruling (auto):`, and each
  other open member PR gets `Ruling (auto): <link to it>.`;
- an issue the Ruling calls for goes under the umbrella, with
  `Part of #U`, only when it serves an acceptance item: a defect this
  feature introduced, or work a target needs. Anything else -- a
  pre-existing defect, an improvement, out-of-scope work -- is filed
  labeled `agent-team/backlog`, with no `Part of` line, and is not claimed.
  Say which in the Ruling's `Also:` line;
- the label removed last, from every member, is `agent-team/ruling`.

**Done when** the item carries its `Ruling (auto):`, its follow-ups are
filed, every item it affects has its comment, and no member keeps
`agent-team/ruling`; or it carries step 4's request and
`agent-team/need-human` in its place. Report the Ruling's or the request's
link and which case decided it.
