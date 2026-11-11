# Design reviewer

You review one design PR (`design.md`) at its current head and post one
verdict. You were given the PR number, the overlay keys and body, and this
skill's directory. A design has no behaviour to test, so the checklist below
replaces the checks of `review.md` step 2; that step's last paragraph, on
what blocks, and its steps 1 (Read), 3 (Delta review), 4 (Post) and 5 (The
loop's own stop) apply as written.

## Read

Besides `review.md` step 1, read what `design.md` step 1 lists: the
requirement document, its Rulings, the indexed design documents, the
principles and the dependencies' handoffs. Before you open the design
document, write down from the requirement document alone its scenarios
(`design.md`, Write the document, says which) and the simplest design you
would accept. If you open it first, its own lists decide what coverage and
simplicity mean.

## Check

Check in your own worktree or `git archive` snapshot of the head, in this
order:

1. **Low confidence first.** An entry that data would settle is blocking:
   it is a spike (`design.md`, End the loop). For the rest, say whether
   the answer holds against its rejected alternative.
2. **A diagram per scenario.** Every scenario on your list and on the
   document's has a diagram, and walking it reaches the scenario's outcome
   through what the Decisions build. A missing scenario, or a diagram that
   skips a step the design must take, is blocking.
3. **The simpler alternative.** The document names one and why it lost. If
   it, or yours, meets every acceptance item and no principle or Ruling
   rules it out, the rejection fails: blocking.
4. **Consistency.** No decision contradicts a decision in the indexed
   design documents, a Ruling on the umbrella or its issues, or a
   principle, unless the document names the conflict and what settles it: a
   Ruling binds its own item, and a project principle beats the default
   list.
5. **Code facts, one by one.** Open every `code:` basis at a freshly
   fetched `<remote>/<integration_branch>` and confirm the path and symbol
   do what the decision says. One false there, even if true at the PR's
   base, is blocking with every decision on it.
6. **Every decision's basis.** Each has one. A `reference:` link resolves
   and shows what is claimed; a `principle:` is in the documents
   `design.md` step 1 reads, since a principle found nowhere there is not
   one.
7. **Within the requirement.** Scope, non-goals and acceptance are the
   requirement document's. A design that changes what to build is
   blocking: it is a requirement gap, for the owner.
8. **Dependencies.** Each spike result matches its issue's handoff, and
   each upstream-only interface has a sync issue.
9. **Size.** A design task is exempt from the line-overrun escalation, so
   size is yours to judge: requirement or code restated outside the
   Summary, a decision with no rival, or a section `plan` would not use is
   a finding.
10. **The rest of the PR.** `<gate_task>` passes at the head; the
    published-text rules (`rules.md`) hold over its whole file set; when
    the issue carries a principles draft, the PR commits it as confirmed.

## Verdict

As `review.md` step 4. `Checked:` names each check above by its number,
with what it found in a few words, so a verdict that skipped one shows it.
