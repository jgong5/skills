# Algorithm language: pseudocode

A figure carries shape, and a source excerpt proves what the code says.
Neither one states the algorithm: a diagram cannot express a condition or an
order, and an excerpt states the algorithm in a language full of detail the
algorithm does not depend on. Pseudocode is the third form -- the algorithm
itself, in the domain's own vocabulary, at one altitude, short enough to hold
in the head. It is also an assertion about what the code does, so every block
is grounded in the Phase 1 step trace and cited by the paragraph beside it.

## When an algorithm earns a block

Write pseudocode for a routine whose control flow is load-bearing: an order,
a condition, a loop, or a state transition that a reader could not
reconstruct from the contract and the figures. The canonical algorithm in the
fixed spine's section 3 always earns one. In the derived middle, the key
algorithms of the implementation earn one each.

A thin delegating wrapper, a getter, or a routine whose body is one call does
not earn a block -- transcribing it into pseudocode teaches nothing and
spends a page. Say plainly that the entry point delegates, and spend the page
on the routine it delegates to.

One notation serves the whole study, canonical form included: in a single
vocabulary, the spine's departures section reads as a diff a reader can see
rather than a paragraph asserting that a difference exists.

## Intuitive, not transliterated

A transliteration is the source rewritten with the syntax filed off -- same
statements, same order, same names, minus the compiler. It costs a page and
adds nothing an excerpt did not already carry. Write the algorithm instead:

- Name each step for what it accomplishes in the domain's vocabulary
  (`relax(dist, queue, node, neighbor)`, `evict the coldest entry`), not for
  the mechanism that happens to implement it (`call _do_relax_inner`,
  `pop from self._q`).
- Keep every step in one block at the same altitude. A block that mixes "take
  the next task" with "increment the byte offset by the header width" is two
  blocks that have not been separated yet.
- Carry only what the algorithm depends on. Logging, type ceremony,
  allocation, and error plumbing are omitted -- unless one of them is the
  decision under study, in which case it is the point and stays.
- Use a small fixed vocabulary, the same one in every block of one study:
  `<-` for assignment, `for each X in Y:`, `while <condition>:`,
  `if` / `else if` / `else`, `return`, `name(args)` for a call, and `#` for a
  short aside. Plain English inside a step is welcome; a language's operators,
  sigils, and decorators are not.
- Keep lines short. Every line inside a fence is checked verbatim against the
  rendered PDF (`rendering.md`), so a wide line is a Phase 4 finding waiting
  to happen.

## Stepwise refinement

Refinement is how a complex algorithm stays readable: the top level states
the whole algorithm at one altitude, and any step whose detail matters
becomes its own block underneath. A step whose detail does not matter is left
as a named call and never expanded -- naming a step is itself an act of
explanation.

Every block is one fence with the info string `pseudocode`, and its first
line is the header that names it:

    ```pseudocode
    procedure <name>(<params>):
        <steps>
    ```

`procedure` opens a root -- one key algorithm, entered from outside the
pseudocode. `refine` opens the expansion of a step that a block above it
calls:

    ```pseudocode
    refine <name>(<params>):
        <steps>
    ```

These rules are a machine-readable contract with `check_pdf.py`
(`PSEUDOCODE_FENCE_RE`, `PSEUDOCODE_HEADER_RE`, `PSEUDOCODE_MAX_STEPS`),
checked in Phase 5:

- the fence's info string is exactly `pseudocode`, and the first non-blank
  line is a `procedure` or `refine` header ending in `(`...`):`;
- every block's name is unique across the document, so a call resolves to one
  block;
- no block has more than 20 steps (non-blank lines after the header). A block
  that overruns is not a formatting problem: refine a step out of it into its
  own block, which is what the reader wanted anyway;
- every `refine` block is called by name from some other block. An expansion
  nothing reaches is detail with no place in the algorithm.

Stop refining at the depth where the remaining detail is mechanism rather
than algorithm -- typically two levels, rarely three. Past that, the reader
is reading the source with extra steps, and the source excerpt is the honest
form.

## A worked example

```pseudocode
procedure shortest_paths(graph, source):
    dist <- {source: 0}
    queue <- [source]
    while queue is not empty:
        node <- take from the front of queue
        for each neighbor of node in graph:
            relax(dist, queue, node, neighbor)
    return dist
```

```pseudocode
refine relax(dist, queue, node, neighbor):
    if neighbor is already in dist:
        return                 # first arrival wins on an unweighted graph
    dist[neighbor] <- dist[node] + 1
    append neighbor to the back of queue
```

The top level is the algorithm: a frontier consumed in arrival order, one
pass per neighbor [C1] [C2]. `relax` holds the invariant that makes it
correct -- a node's distance is written once, on first arrival, so the queue
stays in nondecreasing distance order [C3].

## Evidence boundary

Pseudocode makes claims: that this step happens before that one, that this
branch exists, that this is the loop's exit condition. `check_evidence.py`
skips fenced lines, so a ledger ID typed inside a block is invisible to it
and supports nothing. The paragraph immediately after each block states what
the block establishes and carries the ledger IDs, exactly as the paragraph
after a figure does.

Every step comes from the Phase 1 step trace. A step that has to be invented
to make the block read well is a Phase 1 gap: go back and trace it, or leave
it out. Writing pseudocode is composition, not discovery.

## Placement

Put the canonical algorithm's block in the fixed spine's section 3, and each
implementation algorithm's root block at the head of the derived-middle
section that discusses it, before the prose that explains its consequences.
Put each `refine` block immediately after the block that calls it, so a
reader follows one thread down rather than hunting a page away. A decision
block belongs beside the step it explains, not collected with unrelated
decisions at the end of the section.

Pseudocode and figures divide the work: the execution-flow figure shows which
components the algorithm moves between, and the pseudocode shows the order
and the conditions. When one of them merely restates the other, cut the
weaker one -- two forms of the same thing is a page spent twice.
