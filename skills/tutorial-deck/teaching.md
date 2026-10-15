# Hard rules

These rules bind the outline, the build, and the narrative review. Each has
an ID; the outline's self-check walks them in order, and the narrative
reviewer cites a broken rule by its ID, so a finding names the rule rather
than restating it.

An ID is permanent once a deck has cited it. Add a rule at the end; never
renumber, because a review in an older deck's `reviews/` would then point at
the wrong rule.

The audience is developers new to the topic's theory who must read and
change the code. Every rule below exists because that audience reads a
slide differently from an expert: an expert fills gaps from memory, a
newcomer fills them by guessing, and the guess is what they carry back to
the code.

## R1. Failure first, then mechanism, then code

Before a slide presents a mechanism, the running example shows what breaks
without it. The mechanism then fixes that failure, and the code that
implements it comes last. A "why" box detached from the example does not
count.

Reason: a mechanism shown before its failure is an answer to a question the
audience has not asked. They memorize its shape and cannot tell which part
of it matters, so when they change the code they change the wrong part. A
detached "why" box states a motive without the audience seeing it, which is
the same problem with a heading on it.

## R2. A throughline gets its own slide before its problems

A throughline -- an idea that recurs across several mechanisms -- is
introduced on its own slide before the first problem that instantiates it.
Every later slide that instantiates it names it.

Reason: a recurring idea that is never named is seen as several unrelated
tricks. Naming it once, early, and on every instance after, is what lets the
audience recognise the next instance in code the deck did not cover.

## R3. Diagram over table

When content has structure -- a flow, a hand-off, a state change, a layout
-- draw it. Once a diagram carries what a table held, the table moves to the
slide notes.

Reason: a table makes the audience rebuild the structure in their heads,
row by row, while the speaker talks; a diagram shows it. Keeping both on the
slide splits attention between two copies of one fact. The table stays in
the notes because it is the precise reference a reader wants afterwards.

## R4. One memorable sentence per principle, exception beneath

Each principle is stated as one sentence the audience can repeat. Where it
has an exception, the exception is stated directly beneath it, on the same
slide.

Reason: a principle that takes a paragraph is not remembered, and a
principle remembered without its exception is applied where it is wrong.
The exception belongs beside the rule because that is where it will be
needed.

## R5. Explain every symbol and term where it first appears

A symbol in a formula, a variable in an excerpt, or a term of art is
explained on the slide where it first appears, not on a glossary slide and
not later.

Reason: a newcomer who meets an undefined term stops following the slide to
guess what it means, and the guess often sticks. A glossary at the end
arrives after the confusion has done its work.

## R6. Quantifiers are exact

A claim about a list, a set of cases, or "all" of something holds for every
item. When it holds for most, narrow the claim to the ones it holds for, or
state the exception.

Reason: the audience will act on "every caller does X" when changing a
caller. A claim that is true of most items is false for exactly the item
they will be changing, and they have no way to know it.

## R7. Examples come from the scenario under discussion

An example used to explain a mechanism is drawn from the running scenario
the deck follows -- its request, its data, its configuration -- not from a
generic domain.

Reason: a borrowed example makes the audience translate twice: from the
example to the idea, and from the idea back to the system. A scenario
example is already in the system, so the explanation and its application
are the same step.

## R8. One point per slide; short, cited excerpts

Each slide teaches one thing, the one its outline line names. A code excerpt
is at most about 15 lines, verbatim with `...` elisions only, and carries
its `path: symbol` citation.

Reason: a slide with two points has two places to look and one speaker, so
one point is missed. A long excerpt cannot be read while the speaker talks
over it, and an uncited or edited one cannot be found in the code the
audience must change.

## R9. Unverified claims stay off slides

A claim not traced to the pinned code, `survey.md`, or the replay output
does not appear on a slide. It goes in the slide notes as an open question.

Reason: a slide reads as settled fact. A plausible but unchecked claim on a
slide becomes something the audience believes about the code, and nothing
downstream marks it as a guess. In the notes, it stays visible as a question
for whoever can answer it.
