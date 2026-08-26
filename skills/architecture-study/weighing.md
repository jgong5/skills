# Phase 3: Weigh

Phase 3 is where judgement is finally allowed, and it is allowed only on top
of what Phases 1 and 2 established. It produces the decision inventory that
section 4 is built from, the alternative paradigms that section 6 is built
from, and the open questions that section 7 closes on.

## What counts as a decision

A structural choice qualifies when both are true: a competent engineer could
plausibly have chosen otherwise, and the choice shapes something already in
the inventories -- a seam, a contract's shape, an ownership boundary, a
constraint. Everything else is ordinary prose. Section 4 is not an audit of
every choice the codebase makes; a decision block manufactured to fill the
section costs a page and teaches nothing.

The choices that usually qualify: where state is owned, what crosses each
seam and in what shape, whether ordering is data or code, what the unit of
work is, where the concurrency boundary sits, what is configurable versus
compiled in, and what the system refuses to do.

## Recover the intent before judging it

The deciding constraint is a claim about *why*, and why is the easiest thing
in an architecture review to invent. Work through the available evidence in
this order, and stop as soon as one settles it:

- **The code's own constraints.** Frequently decisive on its own: a choice
  that is the only one satisfying a contract in the inventory needs no further
  explanation, and saying so is stronger than any commentary.
- **Tests.** A test asserting a property is a statement about what the design
  is required to preserve, written by someone who knew.
- **Comments, docstrings, and design notes** at the site of the choice.
- **Commit history.** `git log -p` on the file, and the message of the commit
  that introduced the structure. A revert or a follow-up fix is especially
  informative: it names a failure mode the design now defends against.
- **The forcing function.** When no record survives, derive the constraint
  from `<skill-dir>/paradigms.md`'s forcing functions and say that is what you
  did. "No record explains this; the shape is what the ordering guarantee in
  [K3] requires" is honest and useful.

What is not available: the intent of people you cannot ask. Write "the effect
is X" rather than "the author wanted X" whenever the second is not in
evidence. The report loses nothing -- a reader cares what the design does --
and it stops the most common way a review becomes fiction.

## Name realistic alternatives

An alternative is realistic when it satisfies the same contracts and would
have been available to the authors. One to three per decision.

Guard against the strawman. An alternative that is obviously worse makes the
chosen design look inevitable and teaches the reader nothing, and it is the
default output of asking "what else could they have done" without constraint.
The useful alternative is the one that is genuinely better on some axis and
loses on another -- that is what makes the choice a trade-off rather than a
correction.

State each alternative concretely enough to disagree with: not "a different
data structure" but "a bounded ring buffer sized at admission, which makes the
footprint fixed and makes a burst fail fast instead of queueing".

## Price the trade-off

For each decision, name what the chosen design gives up, on an axis a reader
can check, with the condition that makes it hurt:

- **What gets worse.** Latency at a percentile, footprint per session,
  throughput at a batch size, the number of components a plausible change
  touches, the number of states a reader must hold to understand the path.
- **Under what condition.** The same trigger discipline Phase 2 used. "This
  costs a copy per step" is a fact; "this costs a copy per step, which is
  invisible below a few thousand tokens and dominant above [X4]" is a
  trade-off.
- **What it buys.** The property that is preserved because the cost is paid.
  A decision whose cost buys nothing identifiable is a finding in its own
  right, and it belongs in section 4 stated exactly that way.

The trade-off's supporting claim is a `derive:` entry whose reasoning names
the inventory entries it rests on. This skill runs no benchmarks, so a
trade-off that cannot be settled by derivation is not settled: say which way
it probably goes, say what would decide it, and put the deciding measurement
in section 7.

## Alternative paradigms

Section 6 is one or two whole-system alternatives, not a list of local
substitutions. Each is a different answer to the forcing function section 1
identified: the graph the pipeline could have been, the actor system the
shared-store design avoided, the ahead-of-time compilation the interpreter
replaced.

Each alternative states three things: what it would change structurally,
which constraint in the inventories it would relieve, and **the condition
under which it wins**. That condition is what makes section 6 a design
discussion rather than a preference. "A pass manager would be better" is a
preference. "A pass manager wins once transformations outnumber the people who
can hold the single procedure in their head, roughly the point where [C7]'s
function passes a few hundred lines" is a claim the reader can test against
their own roadmap.

An alternative that is better on every axis is not an alternative paradigm --
it is a bug report, and it belongs in section 5.

## Collect the open questions

Section 7 closes the report with two to four questions, and they are gathered
here rather than invented at writing time. Three sources fill the list:
constraints Phase 2 suspected but could not witness, trade-offs derivation
could not settle, and boundaries the study could not cross.

A question earns its place when the reader can answer it and the report
cannot -- because it depends on production behaviour, on a roadmap, or on a
constraint that was never written down. A question whose answer is already in
the report is a quiz, and it is the fastest way to lose a peer reader's trust.
Aim each one at a boundary: what crosses it, who owns what after it, what
would have to be true for it to move.

## Phase 3 exit criteria

Do not move to Phase 4 until all of the following are true:

- every decision in the inventory shapes something already in the component,
  contract, or constraint inventories;
- every deciding constraint is cited, derived from the inventories, or
  explicitly marked as a forcing-function inference with no surviving record;
- no "the author intended" claim survives without evidence;
- every alternative satisfies the same contracts, and none of them is a
  strawman;
- every trade-off names what gets worse, under what condition, and what the
  cost buys;
- section 6's alternatives each name the condition under which they win;
- two to four open questions are recorded, each one the reader can answer and
  the report cannot.
