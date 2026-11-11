# Default principles

A designer, a design reviewer, and an agent ruling on an escalation weigh a
decision against these when nothing the project states settles it. They
choose how to build, never what: goals and acceptance targets belong to the
requirement. `rules.md` binds every role as well; nothing here repeats or
relaxes it.

A project's own principles document sits in `<design_entry>`'s directory,
indexed by `<design_entry>`. It holds only principles specific to that
project, links this list for the rest, and wins a conflict with it.

Each principle links one Ruling from jgong5/ATOM that decided the same way.

## The simplest solution that meets acceptance

Take the option with the least code and the fewest moving parts that meets
the acceptance targets; a gain past them does not pay for more code, because
every line is read, reviewed and kept working after the task closes.
[Ruling](https://github.com/jgong5/ATOM/issues/2658#issuecomment-6618633303):
one option alone, since the other on top bought 0.02 ms for 80 more lines.

## Measure before deciding

When the choice turns on a number nobody has measured, measure it first and
let the figures pick the option. An estimate argued from memory is how the
wrong option gets built, and a measurement settles it for everyone at once.
[Ruling](https://github.com/jgong5/ATOM/issues/1608#issuecomment-6330659512):
measure first, then build only if the figures call for it.

## Reuse existing code and dependencies first

Use what the project already has, then the standard library and the
dependencies already installed, before writing or adding anything. A second
copy drifts from the first, and a new dependency costs every install.
[Ruling](https://github.com/jgong5/ATOM/issues/2026#issuecomment-6366570534):
reuse the helper another module already calls, shared rather than rewritten.

## No generality for speculative needs

Build for the cases the requirement names; an option, mode or extension point
no one needs yet waits until someone does. Generality costs now, and the need
it guesses at tends to arrive in another shape.
[Ruling](https://github.com/jgong5/ATOM/pull/2683#issuecomment-6578751421):
no per-request model; the one existing setting covers the cells that run.

## Fix shared code, not callers

When shared code is wrong, fix it there once instead of working around it in
each caller (`rules.md`, Escalations, counts the caller-side patch as a
defect). Every caller left unpatched stays broken, and the workaround hides
the cause from the next reader.
[Ruling](https://github.com/jgong5/ATOM/issues/2446#issuecomment-6490597517):
fix the functions' interface; the capture that consumes them stays as it is.

## Prefer reversible choices

Between options that meet acceptance alike, take the one cheaper to undo:
off by default behind a flag, added beside the old path rather than replacing
it. A choice made on partial knowledge is cheap to correct only when it can
be backed out.
[Ruling](https://github.com/jgong5/ATOM/pull/2679#issuecomment-6702896049):
land it, since its flag is off by default and its output is unchanged.

## Follow the project's existing conventions

Name, place and shape new code the way the code beside it already does,
unless changing that convention is the requirement. A reader learns one
convention per job; a second one for the same job costs every later reader.
[Ruling](https://github.com/jgong5/ATOM/pull/2036#issuecomment-6393691362):
an accuracy check runs by `python -m`, as grading already does.

## Change public interfaces only when the requirement does

Keep the commands, flags, file formats and APIs that others call as they are
unless the requirement changes them, and extend an existing one before adding
another. Callers outside the change break without warning, and a published
interface is hard to take back.
[Ruling](https://github.com/jgong5/ATOM/issues/2415#issuecomment-6486902081):
extend an existing command; no new one.
