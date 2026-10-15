# Phase 3: Outline

Phase 3 turns the confirmed `plan.md` into `outline.md`: the deck, one line
per slide, before any slide is built. It also runs the replay script for the
hardest concept. The owner confirms the outline before Phase 4.

The outline exists because a deck's structural faults -- a mechanism with no
failure before it, a throughline named after its first instance, a slide
with two points -- are invisible in a finished slide and obvious in a list
of one-line slides. Fixing them here costs an edited line; fixing them after
the build costs a rebuilt slide and a re-review.

## Line format

One line per slide, numbered from 1, fields separated by ` | `:

```
<n>. <title> | learns: <one thing> | form: <diagram|code|table> | failure: <slide or -> | throughline: <name or ->
```

- **title** is the slide title as it will appear. The build warns when a
  title wraps, so a title that will not fit on one line is shortened here.
- **learns** is the one thing the audience takes away, as a sentence. If it
  needs "and", the line is two slides.
- **form** is how the point is carried. Choose `diagram` unless the content
  has no structure to draw; `code` for an excerpt, which also names its
  `path: symbol`; `table` only for content that is genuinely a lookup.
- **failure** is the number of the slide where the failure this slide's
  mechanism prevents is first shown, or `-` when the slide teaches no
  mechanism (the title, the agenda, a failure slide itself, a throughline
  introduction, a scenario).
- **throughline** is the throughline this slide instantiates, or `-`.

Every line's `learns` traces to an entry in `survey.md`, to the replay
output, or to an earlier slide's `learns`. Keep the trace in your head or in
scratch, not in the line: the line is read by the owner, who wants the deck,
not its bookkeeping.

## Self-check

Before showing the outline, walk the hard rules in `teaching.md` in ID order
against it. Fix every hit in the outline, then walk them again; show the
owner an outline that passes. What each rule means for a one-line slide:

- **R1.** Every mechanism slide's `failure` is an earlier slide number, and
  that slide shows the failure on the main line's scenario, not in a
  separate "why" slide.
- **R2.** Every throughline named in a `throughline` field has its own
  introduction slide, numbered before the first slide that names it, and
  every slide that instantiates it names it.
- **R3.** No `table` slide carries content a `diagram` slide also carries.
- **R4.** A slide whose `learns` is a principle states it as one sentence,
  and its exception, if it has one, is on the same slide.
- **R5.** Every term a `learns` sentence uses is either taught at or before
  that slide, or assumed by the plan's audience.
- **R6.** Every "all", "every", "always" and "never" in a `learns` sentence
  holds for every item in `survey.md`.
- **R7.** Every example a slide needs comes from the plan's main line or
  scenarios.
- **R8.** Every `learns` is one point, and every `code` slide's excerpt fits
  within the limit with its citation.
- **R9.** Every `learns` traces to the pinned code, `survey.md`, or the
  replay output; anything that does not becomes an open question for the
  notes, not a slide.

The narrative reviewer applies the same rules to the built deck. The
self-check is not a substitute for that review; it removes the faults that
are cheaper to fix as a line than as a slide.

Then check the outline against `plan.md`: every in-scope mechanism has a
slide, every throughline has its introduction, the trade-offs and scenarios
are where the plan put them, and the slide count is plausible for the
plan's length.

## The replay script

The hardest concept's step-through needs exact intermediate values. They
come from running the code, not from working the example by hand, because a
hand-worked step-through that disagrees with the code teaches the audience
a mechanism the code does not have.

Propose, write and run the replay script under
`<skill-dir>/../implementation-study/experiments.md`. That doc governs the
whole act: the plan line and its approval, the reproducibility files, the
project's command wrapper, suppressing cache writes into the repository, and
treating a failed run as a result. It ships in the same bundle as this
skill. Read it with these substitutions:

- `<experiments-dir>` is `demo/` in the output directory.
- The plan line names, in place of a ledger ID, the outline slides whose
  numbers the replay feeds, and its `--` part names the runnable core from
  `survey.md` it drives and the toy input from `plan.md`.
- There is no ledger and no `check_evidence.py`. The captured `.out` file is
  cited instead from the notes of every slide that uses its numbers.
- The section on timing applies only when the replay times something; a
  step-through records states, not durations.

The replay drives the runnable core with the toy input and prints each
intermediate state the step-through shows, in the order the slides show
them. Every number on a step-through slide is copied from that output.

When `survey.md` records no runnable core, or the owner does not approve
the replay, hand-derive the step-through. Each slide that carries a
hand-derived number says so in its notes, and the final report lists those
slides. Do not present a hand-derived number as a replayed one.

## Owner confirmation

Show the outline after the self-check passes, together with the replay
proposal. Approving the replay is a separate answer from confirming the
outline: the replay approval is the plan-line approval `experiments.md`
requires, and is asked for as such.

When the replay's output changes a step-through slide's `learns`, show the
changed lines again. Phase 4 starts only after the owner confirms the
outline as it stands after the replay.
