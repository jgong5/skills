# Phase 2: Investigate

Phase 2 turns the comprehension ledger from Phase 1 into a decision
inventory: the places where the implementation chose one thing over another,
what those alternatives were, and what the trade-off actually is. This is
where "how it works" becomes "why it works this way" -- and where the study
either grounds that "why" in evidence, or, when derivation cannot settle it,
names it as a question answered later in this phase, by escalating to
`<skill-dir>/experiments.md` (see "Escalate unresolved questions to
experiments" below) rather than by guessing.

## Build the decision inventory

A decision, for this purpose, is a choice a competent engineer could
plausibly have made differently, and where the difference would actually
matter -- to correctness, performance, memory, concurrency behavior, or
maintainability. Not every line is a decision: a decision is one where a
knowledgeable reader would reasonably ask "why this, and not that?" A
private helper's variable name is not a decision; the choice of a lock-free
queue over a mutex-guarded one is.

For each candidate decision, record:

- the implementation choice actually made, with an evidence ID (from Phase
  1's ledger, or a new one opened here);
- one to three concrete alternatives;
- the observable trade-off between the choice made and the alternatives --
  what would actually be different, not just "it could be done another way";
- the evidence IDs backing all of the above;
- whether the candidate is significant enough to merit its own decision
  block in the eventual study document, or minor enough to fold into
  surrounding prose without one.

## Name realistic alternatives

Reject vague alternatives. "A different data structure" or "some other
approach" is not an alternative a reader can evaluate against the choice
made; "a sorted array with binary search, trading O(1) insertion for O(log n)
lookup" is. An alternative earns its place in the inventory only if it is
something a competent engineer working on this codebase could actually have
reached for -- not a strawman invented to make the actual choice look better,
and not an exotic option nobody in this domain would seriously consider.

## Ground trade-offs

Derive before measuring. If a trade-off follows from something already
cited or already knowable by reasoning -- a data structure's documented
asymptotic complexity, a language's specified semantics, an invariant
established in Phase 1 -- write a `derive:` ledger entry showing that
reasoning rather than reaching for a benchmark. Measurement is for claims
that are genuinely unclear without running code: two implementations whose
relative performance depends on cache behavior, input distribution, or
runtime specifics that reasoning alone cannot settle.

## Use history and external references

Consult `git log`, `git blame`, and any available PR or issue history for
commits that explain a decision -- a commit message citing a regression, a
revert, a comment that used to be there and was removed. Cite external
references (a language specification, a paper, a well-known writeup) by URL
when they explain why a choice was made, alongside the in-repo evidence, not
instead of it.

## Escalate unresolved questions to experiments

When a trade-off is genuinely unclear without running code, do not run
anything from this phase. Instead, read `<skill-dir>/experiments.md`, and
propose the measurement there in its exact plan format. Do not execute
anything until the matching entry has an approved PLAN.md line -- that
approval has to come from the user, not be assumed because the measurement
looks safe or small.

Approval is per-plan: approving one experiment authorizes exactly that
script, for exactly that ledger ID, and nothing else. A revised script, a
different ledger ID, or a discovery mid-experiment that suggests a different
measurement is a new proposal, not a rider on the old approval, and needs its
own approved PLAN.md line -- an amendment, not an assumption. When the user
declines a proposed measurement (or approves only part of a batch), record
the decline in the experiment's PLAN.md and in the ledger, and then either
derive an answer from what is already known or omit the claim. A declined
measurement is not a blocked study; it is a study that is honest about what
it could not establish.

## Phase 2 exit criteria

Do not move to Phase 3 until all of the following exist:

- a decision inventory covering every candidate identified from the Phase 1
  ledger, each with its alternatives, trade-off, and evidence IDs;
- every accepted alternative named concretely, with vague ones rejected;
- every trade-off either derived with reasoning shown, or escalated to
  `experiments.md` with the escalation resolved (approved and measured,
  declined and recorded, or superseded);
- a decision made, per candidate, on whether it becomes a decision block in
  the study document or folds into prose.

A decision inventory that skips grounding and goes straight to writing
prose about "why" is exactly the failure mode this phase exists to prevent:
an unsourced claim that reads as confident and is not.
