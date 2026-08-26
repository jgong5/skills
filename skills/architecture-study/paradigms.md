# Naming what the structure witnesses

Read this once the component inventory is populated. It supplies section 1's
vocabulary and, more importantly, the test each name has to pass before it is
allowed into the report.

Naming a paradigm is not classification for its own sake. A paradigm is a
compressed statement about what the system made variable and what it made
fixed, and a reader who accepts the name inherits a whole set of expectations
about where to look for state, where failures propagate, and what a change
will cost. A wrong name is therefore worse than no name: it sends a competent
reader looking for a scheduler that does not exist.

## The witness test

Three questions, and a name reaches the report only when all three have
concrete answers from the inventory.

1. **Where is the structure?** Point at the data structure or the control
   structure that instantiates the pattern -- the node list, the pass array,
   the dispatch dict, the mailbox, the shared store, the loop that selects.
   A folder called `pipeline/`, a base class called `Handler`, and a docstring
   that says "event-driven" are not structures. They are labels, and they are
   frequently left over from a design the code has since drifted away from.
2. **What varies?** Every paradigm exists to let one thing change without the
   rest changing with it: the set of stages, the order of passes, the number
   of participants, the arrival time of events. Name that thing, and name
   where the variation is expressed -- in configuration, at registration
   time, at runtime. If nothing actually varies, the code is a straight line
   wearing a pattern's clothes, and saying so is a real finding.
3. **What would break it?** Name a change that would violate the pattern --
   a stage reaching backward, a second writer to the owned store, a pass that
   depends on running after another. If no change could break it, the pattern
   is not constraining anything and the name is decoration.

## Catalogue

| Paradigm | The structure that witnesses it | The giveaway that it is not this |
| --- | --- | --- |
| Pipeline | An ordered sequence where stage N consumes stage N-1's output type and nothing reaches backward | Stages read a shared context object, so the order is real but the data flow is not |
| Graph execution | An explicit node/edge structure plus a scheduler that selects ready nodes | The "graph" is only the call stack; the traversal order is fixed at author time |
| Pass manager over an intermediate representation | A shared mutable representation and a pass list that is data, not code | Each pass returns a new representation, or the pass order is hard-coded calls -- that is a pipeline |
| Blackboard | One store with two or more writers, and a control loop that dispatches on the store's contents | A single writer with several readers -- that is ownership plus subscription |
| State machine | A named, enumerable state plus an explicit transition table or dispatch | State is implicit in the program counter and the pattern lives only in a comment |
| Actor / message passing | Independent mailboxes and no shared mutable state across the boundary | Messages carry references into shared memory, so the isolation is nominal |
| Event loop / reactor | One loop demultiplexing readiness across many in-flight operations | The loop is a `for` over a fixed list; nothing is pending, only sequential |
| Ports and adapters | Dependency direction always inward: the core never imports an adapter | The core imports a concrete backend "just for the type hint", which is still an import |
| Registry / strategy dispatch | A key-to-implementation table populated at import or configuration time | A chain of `if backend ==` -- the set is closed, so nothing varies |
| Continuous batching | A scheduler that reforms the batch every step from what has arrived and what has finished | The batch is formed once at admission; that is request aggregation, not continuous batching |
| Middleware chain | Handlers composed so each may short-circuit or transform both directions | Handlers only observe, never transform -- that is a hook list |

## Why a paradigm emerges

Section 1 has to explain why *this* pattern, not merely which one. The
explanation is almost always a forcing function: a constraint the system
faces that leaves few structures viable. Trace the name back to its
constraint.

- **Work with unpredictable latency and no useful ordering** forces an event
  loop or an actor system, because the alternative -- a thread per unit --
  pays a context switch and a stack for every unit in flight.
- **A dependency order not known until run time** forces a graph, because a
  fixed sequence cannot express it. When the order *is* known at author time,
  a graph is overhead, and finding one anyway is a finding.
- **Many independent transformations over one structure** forces a pass
  manager, because the alternative is one procedure that must be re-read in
  full for every new transformation.
- **An open-ended set of participants**, extensible without editing the
  dispatcher, forces a registry or a blackboard. Which of the two depends on
  whether participants need to see each other's intermediate work.
- **Throughput bounded by an accelerator's arithmetic intensity** forces
  batching, and batching that must not make an early arrival wait for a late
  one forces the batch to reform per step.
- **A core that must outlive its backends** forces ports and adapters,
  because every inward import is a future migration.

When a structure's forcing function is absent -- a graph where the order is
static, an actor system inside one process with shared memory anyway -- say
that plainly. Structure without its forcing function is cost without benefit,
and it belongs in section 4 as a trade-off the system is paying for and in
section 5 as complexity that will be maintained forever.

## Real systems are composite

Almost no system is one paradigm. An inference engine is typically a reactor
at the edge, a continuous-batching scheduler in the middle, and a straight
pipeline per step. An agent framework is often a registry of tools, a
blackboard of accumulated context, and a state machine over the turn. A
compiler is a pass manager wrapped in a pipeline.

Name the paradigm **per layer**, and then name the seam where one gives way
to the next -- that seam is usually the most interesting structure in the
system, because it is where two sets of assumptions meet and where the
impedance mismatch, if there is one, lives. A report that picks one global
label for a composite system has thrown away its most useful observation.

## Naming nothing

When no name passes the witness test, write that. "The components are wired
directly to each other and the call graph is the architecture" is a complete,
useful, falsifiable description, and it tells a reader exactly what to expect:
no indirection to trace, and no seam to cut. Reaching for the nearest
approximate label instead is the single easiest way to make an architecture
study untrue.
