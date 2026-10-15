# Phase 6: Revise

Phase 6 runs only when the owner sends feedback on a verified deck. Without
feedback there is no Phase 6; the run ends at the Phase 5 report.

**Treat the feedback as a discussion draft, not a change list.** An owner's
comment on a slide is a reaction to what the slide made them think, and the
edit it implies is often not the edit it names. Applying every comment as
written produces a deck that answers each comment and loses the outline that
held the slides together. So nothing in the deck changes until the owner has
confirmed what will change.

## Read the feedback

Collect every comment with the slide it is about and the text it quotes.

**Group comments that share a cause.** Several comments on different slides
often trace to one fault: a term introduced late, a throughline never named,
a failure shown after its mechanism. Where a group has a common cause, name
it, cite the hard rule in `teaching.md` it breaks if any, and propose one fix
for the group. Fixing each comment separately patches the symptoms and
leaves the cause to produce the next round's comments.

**Look up missing facts before answering.** When a comment asks or implies
something about the code -- "is this really called on every request?" --
read the pinned code, `survey.md`, or the replay output first, and answer
with the source. Asking the owner a fact the code can answer turns their
review into your research.

**Restate a question before answering when unsure what it asks.** A comment
that can be read two ways gets its reading stated back -- "you are asking
whether X, not Y?" -- before any answer or proposal. An answer to the wrong
reading costs a round and reads as evasion.

## Propose, then edit

Reply to the feedback as a list of proposals: for each comment or group, the
slides affected, the change, and the reason, with the source for every fact
it adds. A comment you propose not to act on gets its reason too.

**Edit only after the owner confirms.** Confirmation is per proposal: an
owner who confirms some and questions others has confirmed only those. A
change that is a teaching decision -- a new throughline, a reordered main
line, a different scope -- updates `plan.md` and `outline.md` first, and the
outline's self-check runs again on the changed lines.

Then edit `build.js`, rebuild, and fix every deckkit warning, as in Phase 4.

## Re-verify

Run Phase 5 on the changed slides and the slides adjacent to them, as its
later rounds do: a changed slide can break the one before it (a term now
used before it is taught) or after it (a failure the next slide relied on
now gone). Re-render first; the reviewers see the deck as it now is.

Record the feedback, the confirmed proposals, and the re-verification's
findings and dispositions in `reviews/`, alongside the Phase 5 rounds, so
the deck's history of what was asked and what changed stays in one place.

Report to the owner what changed, by slide, and anything the re-verification
left open.
