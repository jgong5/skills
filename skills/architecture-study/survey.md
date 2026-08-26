# Phase 1: Survey

Phase 1 decides what the report is about and writes down what is true before
anything is interpreted. It produces three things in
`<stem>_architecture.notes.md`: the declared boundary, the component
inventory, and the contract inventory -- each entry backed by a ledger entry
this phase also opens. Nothing here is a judgement. "The scheduler owns the
queue" is Phase 1 work; "owning it there was the right call" is Phase 3's.

## Safety preflight

Before reading anything, establish the baseline that makes the read-only
invariant checkable.

In a git work tree, confirm `git status --porcelain` is empty and record that
in the notes. A dirty tree is not a hard stop, but every path already dirty
has to be listed in the notes now, because Phase 6 compares against this
moment and cannot otherwise tell your edit from the one that was already
there.

Outside a work tree, take the snapshot instead, through the project's command
wrapper:

    <skill-dir>/check_evidence.py snapshot \
        --repo-root <repo-root> --output-dir <output-dir> \
        --snapshot <stem>_architecture.integrity.json

Every file the study will cite must be inside the snapshot. When Phase 2 or
Phase 3 cites a file the snapshot does not cover, extend it with
`extend-snapshot` and `--cited-file` rather than retaking it -- a retake would
launder a change made since the baseline into the new baseline.

## Declare the boundary

**The boundary is exactly the set of files you open and read.** Not the
directory tree, not the package list, not what the README says the system
contains. A component whose source you did not read is outside the boundary
however central it is, and the report says so.

That rule exists because the cheapest way to write a confident architecture
review is to read the directory listing, recognise the folder names, and
describe the architecture those names imply. The result is fluent, plausible,
and unfalsifiable. Reading is the only thing that separates a review of this
system from a review of the system its layout resembles.

Work outward from entry points, not downward from the root. Find what the
outside world actually calls -- the CLI parser, the HTTP handler, the
public `__init__`, the registered plugin hook, the test suite's setup -- and
follow the wiring from there. Stop expanding at a component that is reachable
only through an interface you can describe accurately from its signature and
its call sites, without reading its body.

Every place you stop is a **boundary edge**, and each one is recorded now with
the reason: too large to read closely, a third-party dependency, a stable
interface whose internals do not change the story, or a subsystem the user
scoped out. The `**Boundary.**` block in the report is written from this list.
An edge that goes unrecorded reads, in the finished PDF, as a component that
does not exist.

If the honest boundary is still too large to read closely, narrow it and say
what you narrowed to. A narrower boundary read properly beats a wider one
skimmed, and the difference is visible to any reader who knows the system.

## Build the component inventory

One entry per component inside the boundary. A component is a unit with its
own state or its own responsibility, not a file -- one file can hold three,
and one component can span a package.

For each, record:

- **Name and files.** The paths you read, so the boundary stays auditable.
- **What it owns.** The mutable state whose writes it is the only source of.
  Ownership is the load-bearing question and the one most often assumed:
  before writing "the scheduler owns the queue", find every write to that
  queue in the boundary. Two writers is not ownership, it is a shared store,
  and that distinction changes which paradigm section 1 names.
- **What it does.** One sentence, at altitude, in the domain's vocabulary.
- **Who calls it, and what it calls.** Actual call sites inside the boundary,
  plus the boundary edges it reaches.
- **How it is wired.** Constructed where, injected how, discovered through
  what registry. Wiring is where a system's real coupling lives, and it is
  invisible in a file listing.

## Name what each structure witnesses

Read `<skill-dir>/paradigms.md` once the inventory is populated -- not before.
It supplies the vocabulary for section 1 and the structural test each name
has to pass. Naming a paradigm before the inventory exists is how a system
gets described as the pattern its folder names suggest.

## Build the contract inventory

A **seam** is a boundary you could actually cut: replace one side with a
different implementation and the other side would not notice. Every candidate
seam in the component inventory gets tested against that sentence, and the
ones that fail are the interesting ones.

One entry per seam, recording:

- **The two sides and the direction.** Who calls whom, or who publishes and
  who subscribes.
- **What crosses.** The precise shape, not the parameter names: the dataclass
  and its fields, the tensor's dtype and layout, the dict's actual keys, the
  intermediate representation's node types, the prompt template and the slots
  filled into it, the serialized envelope. "A config object" is not a
  contract; the twelve fields three components each read a different four of
  is.
- **Who allocates it and who owns it afterward.** Whether the callee may
  retain it, mutate it, or free it, and whether the caller may keep using it.
  A contract that never says is a contract both sides are guessing at.
- **What is guaranteed.** Ordering, idempotence, thread affinity, error
  taxonomy, what happens on partial failure.
- **What leaks.** A contract leaks when the caller must know something about
  the callee's implementation to use it correctly: call this before that, do
  not call it from that thread, this returns `None` twice before it works,
  this field is only set when that backend is active. Every leak is a
  coupling section 2 has to report and section 5 has to price.

## Open the ledger

`<stem>_architecture.notes.md` holds the ledger, and every claim that reaches
the report comes from it. One entry per line, in exactly this grammar:

```
- [ID] <claim>. <class>: <source>
```

The bullet's shape is a machine-readable contract with `check_evidence.py`: a
line counts as an entry only when it starts, with no leading whitespace,
exactly `- [` -- one hyphen, one space, one bracket -- followed by an ID
beginning with an uppercase letter and ending in a digit. A near miss (`* [C1]`,
`-  [C1]`, `- [c1]`) is not reported as malformed; it is silently not an
entry, and the failure surfaces much later as "prose references unknown ledger
id C1" while the entry sits in the notes with a one-character typo.

Two evidence classes reach an architecture study:

```
- [C1] The scheduler owns the request queue. cite: engine/sched.py:41 `self._queue = deque()`
- [X2] Every enqueue blocks the event loop. derive: C1, C4 -- the deque is guarded by a threading.Lock acquired on the loop thread, so a contended enqueue parks the loop rather than yielding.
```

`cite:` names a `path:line` or `path:line-line` plus a verbatim, backticked
anchor -- the exact substring of that line -- so a moved or edited anchor is
caught mechanically instead of trusted. `derive:` names the IDs the reasoning
rests on and shows the reasoning after ` -- `; the checker requires those IDs
to exist and the derivation graph to be acyclic, but it cannot check that the
reasoning is sound. That stays the author's job, and a derivation whose ` -- `
clause is a restatement rather than an argument is the most common way an
unsupported claim reaches a finished report.

`check_evidence.py` also understands a third class, `measure:`. This skill
does not use it. An architecture study is a reading exercise; a claim that
needs a benchmark before it is credible is a question for section 7, not a
measurement this review runs. Say "this looks like the bottleneck and we did
not measure it" rather than implying you did.

Prefix IDs by inventory so the ledger stays navigable as it grows: `C` for
components, `K` for contracts, `X` for constraints, `D` for decisions. Every
ID ends in a digit -- `K1`, `X12`, never a bare `K`.

## Phase 1 exit criteria

Do not move to Phase 2 until all of the following are true:

- the integrity baseline exists -- a clean `git status` recorded, a listed set
  of already-dirty paths, or a written snapshot;
- every component in the inventory names files that were actually opened, and
  every component that was not opened appears instead as a boundary edge with
  a reason;
- every "owns" claim was checked by finding all writers of that state inside
  the boundary, not inferred from a name;
- every seam records what crosses it in its actual shape, who owns it
  afterward, and what it leaks;
- every paradigm name proposed for section 1 has a structural witness in the
  ledger, per `<skill-dir>/paradigms.md`;
- every entry in all three inventories has at least one ledger ID, and every
  `cite:` anchor was copied from the file rather than typed from memory.
