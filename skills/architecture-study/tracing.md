# Phase 2: Trace

Phase 2 follows one concrete execution from entry to exit through the
components Phase 1 read, and writes down what actually happens on the way. It
produces two things in the notes: the **step trace** that section 3 is built
from, and the **constraint inventory** that section 5 is built from. Both come
from reading the path, not from knowing how systems like this usually work.

## Choose the traced loop

Pick one execution and name it. The default choice is the path the system's
callers exercise most -- a single request served, one compilation of one
module, one agent turn, one training step, one simulation tick. Where several
paths are equally central, pick the one that touches the most seams, and say
in the report which one you picked and how the others differ.

This is **the traced loop**, and the whole report refers back to it. A report
that describes five paths shallowly teaches less than one that follows a
single path all the way down, because only the second one can say where the
state actually lives.

## Trace it by reading, not by pattern

Every step in the trace names the location where control passes: a file and a
line. That constraint is the point of the exercise. A lifecycle written from
familiarity with the genre -- "the request is validated, then routed, then
dispatched to a worker" -- reads exactly like a lifecycle written from the
code, and the only difference visible to a reader is that the first one is
sometimes wrong about which component holds the lock.

When the path reaches a boundary edge, stop and record what crossed it and
what came back. Do not describe what happens inside a component whose source
Phase 1 did not read.

Where the path forks, follow the common case and record the fork. Where it can
fail, follow at least one failure to its handler: error paths are where
ownership assumptions are usually broken, and they are the part of a
lifecycle that no reader can reconstruct from the happy path.

## What each step records

One entry per step, each with its ledger IDs:

- **Where control is.** The `path:line` the step begins at.
- **What state it reads or mutates.** Named, and attributed to the component
  Phase 1 said owns it. A mutation of state some *other* component owns is
  not a step detail -- it is a finding, and it goes straight into the
  constraint inventory as a coupling.
- **What it allocates, and what frees it.** The buffer, the tensor, the
  request object, the accumulated context, the intermediate representation.
  For anything whose size scales with input, record what it scales with.
  Note where a copy is made that could have been a view, and where a view is
  kept that pins a much larger allocation alive.
- **What crosses which seam.** Reference the contract inventory entry rather
  than restating the shape.
- **What it waits on.** A lock, a network round trip, a device queue, a
  subprocess, a file, a barrier, another task's completion.

## Hunt the blocking points

The steps that wait are the raw material for section 5, but a step that waits
is not yet a constraint. A constraint is a wait that costs something *because
of how this system is built*, and the difference is the mechanism.

For each waiting step, work out and record:

- **What the wait serialises.** Which other work cannot proceed while this
  one waits. A blocking call on a thread that has nothing else to do costs
  nothing; the same call on the thread that also runs the event loop costs
  every in-flight request.
- **Who else is holding what.** A lock held across an await, a `GIL`-bound
  section on the hot path, a single connection pool shared by every worker, a
  global cache behind one mutex.
- **What grows.** Any structure that gains entries faster than it loses them
  under a plausible load: an unbounded queue, a cache with no eviction, a
  history that accumulates for the life of a session, a retry list.
- **The trigger.** What has to be true for this to actually bite -- a
  concurrency level, a payload size, a session length, a cache miss rate.
  A constraint without a trigger is not falsifiable, and section 5 is
  supposed to be a set of claims a reader can go and disprove.

## Structural constraints, not just runtime ones

Not every vulnerability is a stall. The other kind is change amplification,
and it is measured the same way: pick a plausible change -- add a backend, add
a field to the request, change the batching policy, swap the transport -- and
count the components inside the boundary that must be edited together. Record
the count and the names.

That number is the honest version of "tightly coupled". It has a witness (the
components), a trigger (the change), and a reader can check it. The adjective
on its own has none of the three, and section 5 does not accept it.

## Every constraint needs a witness

This is where the witness rule earns its keep. A report on a Python service
will attract "the Global Interpreter Lock serialises CPU-bound work"; a report
on anything calling a model will attract "inference latency dominates"; a
report on any accumulating context will attract "memory footprint grows
unboundedly". Each of those is true of the world and says nothing about this
system.

A constraint enters the inventory only with a `path:line` for the mechanism:
the call that blocks, the lock that is held, the structure that grows, the
component that must change. When the mechanism is suspected but not found --
it looks like the bottleneck, and reading did not settle it -- it is not a
section 5 finding. It is a section 7 question, and phrasing it as one is more
useful to the reader than a confident guess, because it tells them exactly
what to go measure.

## Phase 2 exit criteria

Do not move to Phase 3 until all of the following are true:

- the traced loop is named, with a stated reason for choosing it and a note on
  how the other paths differ;
- every step names a `path:line`, and no step describes the internals of a
  component outside the boundary;
- at least one failure path was followed to its handler;
- every allocation whose size scales with input records what it scales with;
- every mutation of state owned by another component is recorded as a coupling
  in the constraint inventory, not left in the step trace;
- every constraint has a mechanism at `path:line` and a trigger stating what
  makes it bite;
- every suspected-but-unwitnessed bottleneck is written down as a candidate
  section 7 question rather than kept as a finding.
