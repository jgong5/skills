# Phase 2: Interview

Phase 2 settles every decision the deck depends on, one at a time, with the
owner. It ends in `plan.md`, which the owner confirms before Phase 3 starts.

## How to ask

**One decision per question.** Each question carries a recommended answer,
the reason for it, and the `survey.md` entry the reason rests on. The owner
then accepts, picks another option, or says something new. Several decisions
in one message get one answer for the first and silence for the rest, and
the silence is later read as agreement.

**Facts are looked up, never asked.** Whether a function is called on every
request, which issue fixed a bug, what a config default is: read the code or
the records. A question about a fact hands the owner work the skill can do,
and an owner answering from memory can be wrong where the code is not. If
the lookup cannot settle it, the fact goes in `survey.md`'s open questions;
it is still not an interview question.

**A recommendation is grounded or it is not made.** When `survey.md` gives no
basis to prefer one option, say so and ask without a recommendation. An
ungrounded default looks like a finding and gets accepted as one.

Ask in the checklist's order. The order matters only at the start: each
later item can be revisited when an answer changes an earlier one, and a
revisited decision is asked again rather than silently updated.

## Decision checklist

1. **Output directory.** Asked first, before any other work is spent. Every
   artifact of the run lands there, and an existing directory stops the run
   with a question, so a collision is found while it costs nothing.
   Recommend `<stem>_deck/` in the current working directory, with `<stem>`
   a short slug of the topic. If the recommended path exists, say so and ask
   for another; never write into an existing directory. Write `survey.md`
   into the new directory as soon as this is answered.
2. **Audience.** What the audience already knows and what they will change
   in this code. The default audience is developers new to the topic's
   theory; this decision says which theory is new and which background can
   be assumed, and every hard rule about explaining terms depends on it.
3. **Scope.** Which concepts and mechanisms from `survey.md` are in the deck
   and which are named as out of scope. Recommend the set the main line
   passes through; a mechanism the main line never reaches is a detour.
4. **Length.** The talk's total minutes. Slide notes carry per-slide minutes,
   and the build warns when their sum is off this figure by more than the
   allowed margin, so this is the number the deck is held to.
5. **Language.** The language of the slide text and the notes. Code,
   identifiers and quoted log lines stay as they are in the source.
6. **Fonts.** The body and code fonts. The defaults are Microsoft YaHei and
   Consolas; override when the deck's language or the venue needs another.
   A font missing on the render machine does not stop the run, but the
   visual reviewer and the final report are told.
7. **Opening.** How the deck motivates the system.
8. **Main line.** The one request or datum the deck follows.
9. **Throughlines.** The ideas that recur across mechanisms and get their own
   slide before their first instance. Recommend only ideas that `survey.md`
   shows in at least two mechanisms; a throughline with one instance is a
   mechanism.
10. **Hardest concept.** The concept the audience is least likely to follow,
    and the toy example that steps through it.
11. **Trade-offs.** Which design decisions are taught, and which are large
    and which small.
12. **Developer scenarios.** The closing scenarios.

## Interview defaults

The opening, main line, hardest concept, trade-offs and developer scenarios
each have a default shape. Recommend it unless `survey.md` gives a reason not
to; the owner may override any of them.

- **Opening: escalate naive approaches until the system is necessary.**
  Start from the simplest thing that could work, show where it breaks, fix
  that, and repeat until the next fix is the system itself. Each step is a
  failure the audience has now seen, which is what the hard rules require
  before each mechanism; the opening pays that debt for the system as a
  whole.
- **Main line: follow one request or datum through the system.** One
  concrete thing moving through the code gives every mechanism a place in
  time and a reason to exist at that moment. Recommend the request or datum
  that passes through the most in-scope mechanisms, and name the `survey.md`
  entries it touches.
- **Hardest concept: a step-through toy example before its formula.** Walk a
  small instance through the mechanism one state at a time, then state the
  general rule the steps followed. A formula shown first is symbols without
  referents; shown after the steps, each symbol names something the
  audience has already watched change. The step-through's numbers come from
  the replay script Phase 3 runs, or are marked hand-derived.
- **Trade-offs: one reasoning chain, small ones inline, a closing map.**
  Large trade-offs are taught as one chain after the mechanisms, because
  each depends on mechanisms the audience must already know. Small ones are
  stated inline, on the slide of the mechanism they shape. The deck closes
  with a decision map of every taught decision. Each decision is shown as
  problem, candidates, choice, cost, with numbers copied from the design
  records in `survey.md`; a decision without recorded numbers is shown
  without numbers, never with estimated ones.
- **Developer scenarios: symptom, cause, where to change, which check
  catches it.** The audience will meet the code as a bug report or a feature
  request, not as a lecture. Each scenario starts from what they will see,
  traces it to the mechanism, names the `path: symbol` to change, and names
  the test or check that would catch a wrong change. Prefer scenarios built
  from `survey.md`'s real incidents.

## `plan.md` template

Write `plan.md` in the output directory with one field per checklist item,
in the checklist's order. A field's value may continue on lines indented by
two spaces. Leave no field empty: an item the owner declined to decide is
written as the recommended answer with "(default)" after it.

```
# Plan: <topic> at <pin>

Output directory: <path>
Audience: <what they know; what they will change>
Scope: <in-scope concepts and mechanisms; named exclusions>
Length: <total minutes>
Language: <slide and notes language>
Fonts: <body font>, <code font>
Opening: <the naive approaches, in order, and where each breaks>
Main line: <the request or datum, and the survey.md entries it passes>
Throughlines: <name: the mechanisms that instantiate it>
Hardest concept: <the concept; the toy example; the runnable core, or none>
Trade-offs: <large: the chain, in order; small: each with its slide topic>
Developer scenarios: <symptom; cause; where to change; which check>
```

Show the finished `plan.md` to the owner and get an explicit confirmation
before Phase 3. A plan the owner has not confirmed is a draft, and an
outline built on a draft is rebuilt when the draft changes.
