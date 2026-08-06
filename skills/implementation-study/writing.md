# Phase 3: Write

Phase 3 turns the Phase 1 ledger and the Phase 2 decision inventory into
`<stem>_study.md`. Nothing new is discovered here -- if a sentence needs
evidence that Phase 1 or Phase 2 did not produce, that is a sign to go back,
not to write around it. Two later phases read this document mechanically,
not just a human: `check_pdf.py` and `check_evidence.py`, both in Phase 5.
Both are described here beside the rule they enforce, because a contract
that lives only in a script's regex is a contract nobody writing prose can
see.

## Evidence references and claim discipline

Cite evidence inline with the ledger ID in brackets: "the queue is a deque,
not a list [C1]." Every substantive contract, behavior, complexity,
rationale, and improvement-condition claim gets one or more ledger IDs;
string several together when a sentence rests on more than one
(`[C3][C7]`). Connective prose -- "first," "this means," "as a result" --
does not need a fake citation; the rule is that every claim a skeptical
reader could ask "says who?" about has an answer, not that every sentence in
the document carries a bracket.

An unused ledger entry is allowed on purpose: Phase 1 and Phase 2 often turn
up evidence that does not make the final cut, and `check_evidence.py` does
not flag a `[C9]` that the prose never mentions. What it does flag is the
reverse -- a `[C9]` the prose cites that the ledger does not define. Nothing
mechanical catches a claim that should have carried a citation and did not;
that is caught by reading the document once, start to finish, asking of
every sentence whether it needs one.

The ledger entry itself, in `<stem>_study.notes.md`, has the exact grammar:

```
- [ID] <claim>. <class>: <source>
```

This format and the backticked file anchor below are a machine-readable
contract with `check_evidence.py` (`ENTRY_RE`, `FILE_CITE_RE`); change the
prose and the parser together or one silently stops enforcing the other.
Three classes, three shapes for `<source>`:

```
- [C1] The queue is a deque, not a list. cite: bfs.py:12 `queue = deque()`
- [C2] Insertion is O(1). derive: C1 -- deque append is documented O(1); no resizing copy on the hot path.
- [C3] The batched variant is 2.1x faster on the 10k-node fixture. measure: bench_queue.py -> bench_queue.out
```

`cite:` names a `path:line` or `path:line-line` plus a verbatim, backticked
anchor -- the exact substring of the cited line -- so a moved or edited
anchor is caught mechanically instead of trusted on the honor system.
`derive:` names the ledger IDs the reasoning rests on and shows that
reasoning after ` -- `; `check_evidence.py` requires the IDs to exist and
the derivation graph to be acyclic, but it cannot check that the reasoning
itself is sound -- that is still the author's and the reviewer's job.
`measure:` points a script at its captured output (`script -> output`),
and `check_evidence.py` requires both to exist in an experiments directory
next to an `ENV.md` and an approved `PLAN.md` line; write the measurement's
result plainly in the prose, including a result that contradicts what the
decision inventory expected.

Ledger IDs must end in a digit (`C1`, `PERF3`, never bare `PERF`).
`check_evidence.py`'s own reference regex only recognizes an ID ending in a
digit, and `parse_ledger` now rejects any entry ID that regex would not
recognize -- so a bare-word ID is a hard parse error in Phase 5, not a
silent gap. Number every ID from the start so this never comes up.

Bracketed, all-uppercase text in prose reads as a ledger reference whether
or not that is what it is. `check_evidence.py` scans every non-fenced line
of the study document for `[BRACKETED-UPPERCASE]` and treats each match as
a citation to check against the ledger; it does not know the difference
between `[C7]` and "the [CPU] scheduler" or "a [TODO] left behind." Writing
either of the latter in running prose produces a spurious "prose references
unknown ledger id" failure at Phase 5. Spell an acronym out in prose ("the
CPU scheduler") or put it inside a fenced code block; reserve bracketed
all-uppercase text for ledger IDs.

The bullet's exact shape matters as much as the ID's shape. A line is
recognized as a ledger entry only when it starts, with no leading
whitespace, exactly `- [` -- one hyphen, one space, one opening bracket --
followed by an ID beginning with an uppercase letter (`ENTRY_PREFIX_RE`:
`^- \[[A-Z][A-Z0-9_-]*\]`). A near-miss does not raise an error and does
not appear in any PROBLEM: line. It simply is not a ledger entry as far as
the parser is concerned, so it vanishes from the ledger without a trace:

- a different bullet marker (`* [C1] ...`, `+ [C1] ...`);
- wrong spacing (`-  [C1] ...` with two spaces, or `-[C1] ...` with none);
- an ID that does not start with an uppercase letter (`- [c1] ...`,
  `- [1a] ...`).

Any of these reads as ordinary prose, not a malformed entry, so
`check_evidence.py` has nothing to reject. The failure this produces is
indirect and can be confusing: a claim that cites `[C1]` in the study
document now points at an ID the ledger silently never defined, and Phase
5 reports "prose references unknown ledger id C1" -- a missing-reference
error, not a malformed-entry error, even though the entry is sitting right
there in the notes file with a one-character typo. There is no looser regex
that could safely catch every near-miss without also rejecting legitimate
prose that happens to start a line with a hyphen, so this is a rule for the
author, not the checker: write the bullet in the exact grammar above,
character for character, and check for it explicitly during the Phase 3
read-through -- the parser will not tell you when a bullet was almost
right.

## Fixed spine

The document opens with these five sections, in this order, every time:

1. What it computes -- inputs, outputs, preconditions, postconditions,
   failures.
2. Where it sits -- real callers, nearest public API path, dependents; say
   plainly when no callers exist.
3. Background and the canonical algorithm -- only load-bearing concepts,
   the standard name and form, pseudocode, complexity, an external source;
   say plainly when no canonical form exists.
4. How this implementation departs from the canonical form -- the deltas
   from that standard form, or the design as a whole when the
   implementation is bespoke and there is no canonical form to depart from.
5. Data structures and invariants -- the state the implementation keeps
   and the truths it maintains about that state.

This order is fixed because a reader needs the contract and the standard
form before "how it departs" means anything, and needs both of those
before "what state it keeps" can be read as a consequence rather than a
list of facts. Skipping a section because it feels thin is not an option;
say plainly that there are no callers, or no canonical form, rather than
omitting the heading.

## Diagram-first composition

Read `<skill-dir>/diagrams.md` before drafting the body. The document is not a
prose report with pictures added afterward: the figures establish the reader's
mental model, and prose explains the consequence. Place the canonical
`data-diagram="implementation-structure"` figure after "Where it sits", the
`data-diagram="execution-flow"` figure around "Data structures and invariants"
or at the opening of the derived middle, and the
`data-diagram="decision-landscape"` figure before the detailed decision blocks.

Every factual node, edge, transition, and comparison is an assertion. It must
come from Phase 1's visual inventory or Phase 2's decision inventory, and the
paragraph immediately after its figure states the takeaway with ledger IDs.
Citations stay in ordinary prose, not only inside SVG, because
`check_evidence.py` verifies Markdown references rather than interpreting a
drawing. If the inventories do not support a relationship, return to the phase
that should establish it or omit it.

Number captions `Figure N. Title`, from 1 without gaps, and refer to each as
`Figure N` in adjacent prose. Add a supplemental state-machine, data-layout,
lifecycle, concurrency, or algorithm-stage figure whenever it makes a
load-bearing relationship visible more directly than a paragraph can. Then cut
the paragraph that merely recites its nodes and arrows: interpretation should
explain causality, caveats, and why the picture matters, not duplicate it.

The literal role names, SVG metadata, CSS classes, accessibility requirements,
and drawing recipes are the machine-readable contract in `diagrams.md`. Use
that markup exactly. These are load-bearing figures, not decoration, and
`check_pdf.py` checks both their source structure and whether their visible text
survived rendering.

## Derived middle

After the fixed spine, the document follows the implementation's actual
structure, not a second universal template. What goes here depends on what
Phase 1 and Phase 2 actually found: the phases the algorithm passes
through, the state machine it implements, the concurrency protocol it
follows -- whatever shape the code itself has. A study of a two-phase
commit implementation organizes its middle around the two phases; a study
of a cache organizes its middle around eviction, lookup, and invalidation.
Impose the code's own structure on the reader instead of forcing the code
into a structure the code does not have.

## Decision blocks

A decision block is exactly three parts, in this order, with the labels
written verbatim, each starting its own line and separated by a blank line:

```markdown
**Decision.** <what the code does>

**Alternatives.** <one to three realistic other choices>

**Why this one.** <cited or derived trade-off with [C1] references>
```

The blank line between the parts is a rendering rule, not a parser rule, and
it is the one part of this shape Phase 5 cannot catch. Markdown folds
adjacent lines into a single paragraph, so a block written as three adjacent
lines passes `check_pdf.py` -- which reads the markdown, never the rendered
page -- and then renders in the PDF as one run-on paragraph with three bold
labels buried mid-sentence, which is exactly the structure the block exists
to make visible. Separating the parts with blank lines changes nothing
mechanically: a blank line never closes a block, so all three markers still
belong to the same block, and only the next `**Decision.**` or the next
`## ` heading closes it.

The literal markers, their exact wording, and their order are a
machine-readable contract with `check_pdf.py` (`DECISION_MARKERS`): the
checker's parser matches `**Decision.**`, `**Alternatives.**`, and
`**Why this one.**` as literal text at the start of a line, in that order,
and reports a block as incomplete or out of order if any label is missing,
reworded, or reordered. Concretely, that means:

- Every marker line must begin at column zero -- no leading whitespace, no
  indenting inside a list item or blockquote. A marker seen anywhere but
  the start of the line does not match and the block is invisible to the
  checker.
- The three markers must appear in exactly this order -- `**Decision.**`
  first, then `**Alternatives.**`, then `**Why this one.**` -- with nothing
  else recognized as a marker in between. Swapping `**Alternatives.**` and
  `**Why this one.**` is reported as "parts out of order," not silently
  accepted.
- `**Decision.**` opens a new block and closes whatever block was open
  before it (missing parts and all); a Markdown heading (`## `) also closes
  whatever block is open. A block cannot span past the next `## ` heading
  or the next `**Decision.**` line, whichever comes first.
- An `**Alternatives.**` or `**Why this one.**` line with no open
  `**Decision.**` block before it is not a valid decision block on its
  own -- the parser only starts a block on `**Decision.**`, so an orphaned
  `**Alternatives.**` or `**Why this one.**` is simply dropped rather than
  reported as an error. Always open with `**Decision.**` first.
- Do not reword the labels ("**The decision:**", "**Alternative
  choices.**") even when the reworded version reads more naturally --
  a label the regex does not match makes the whole block invisible to
  Phase 5, not just cosmetically different.

Use a decision block only when a competent engineer could plausibly have
chosen differently and the choice matters -- the same bar Phase 2 used to
build the decision inventory. A choice with no real alternative, or a
choice too minor to matter, belongs in ordinary prose instead: not
everything the implementation does needs the machine-readable weight of a
full block.

## Improvements and back matter

Four chapters close every study document, always in this order. The first
three are authored; the fourth is generated from the notes ledger:

- **Improvements.** One entry per credible improvement Phase 1 and Phase 2
  surfaced but the implementation does not take. Each entry states what
  changes and what has to be true for that change to actually win --
  falsifiable, not aspirational. "Batching would help" is not an
  improvement entry; "batching writes would help when write volume exceeds
  roughly N/s, because below that the batching overhead itself dominates
  [C11]" is, because a reader could go find out whether that condition
  holds and be proven wrong.
- **Boundary note.** Every component Phase 1 pushed outside the study
  boundary, named plainly, with why it was excluded. This is where "we did
  not look at X" is said out loud instead of silently implied by its
  absence.
- **Sources.** Every external reference used anywhere in the document --
  specifications, papers, writeups -- listed once, so a reader does not
  have to hunt back through the prose to find a URL cited only inline.
- **Evidence ledger.** The terminal, generated definition of every inline
  `[ID]`: claim, evidence class, and source. This makes the Markdown and PDF
  self-contained; a reader never needs the companion notes file to decode a
  mark such as `[C1]`. The notes file remains the single authored source of
  truth. Never type or edit this chapter by hand. After all authored prose and
  notes are final, invoke through the project's command wrapper:

      <skill-dir>/check_evidence.py materialize-ledger \
          <stem>_study.md <stem>_study.notes.md

  The command creates or replaces the managed terminal chapter
  deterministically. If the notes change, rerun it before Render;
  `check_evidence.py verify` rejects a missing, stale, reordered, or edited
  projection.

Inline IDs remain required even though their definitions now appear at the
end. They connect each sentence to one precise definition; the appendix makes
that connection usable inside the deliverable rather than replacing it with
uncited prose. `Sources` and `Evidence ledger` also have different jobs:
Sources deduplicates external references, while Evidence ledger defines every
code citation, derivation, and measurement used by the study.

## Code excerpts, headings, and cross-references

Number every top-level section heading `## N. Title`, starting from 1, with
no gaps and no repeats. That sequencing is a writing convention for the
reader, not something either checker verifies: `check_pdf.py`'s
`HEADING_RE` (`^##\s+(\d+)\.\s`) only extracts each heading's number into a
set, and a set has no memory of gaps or duplicates -- two sections both
numbered `## 3.` collapse into one entry `{3}` and neither the second
heading nor a gap at, say, `4` is ever reported. What `HEADING_RE` and
`XREF_RE` mechanically enforce is narrower and different: that every
cross-reference in the prose resolves to some heading number that exists.
Phrase a cross-reference as `section N` or `sections N and M` -- this is
`XREF_RE` (`\b[Ss]ections?\s+(\d+)(?:\s+and\s+(\d+))?`), which looks up
each number it finds against the set `HEADING_RE` built and reports only a
reference to a number missing from that set. "See the section above" or
"as discussed earlier" is invisible to this check and is not a substitute
for `section N` when precision matters. Keep the numbering itself
sequential and unique by discipline, the same way the ledger's IDs are --
the checker will catch a broken forward reference, but it will not catch a
skipped or repeated section number, and a reader will notice both.

Every non-blank line inside a fenced code block is checked, mod
whitespace, against the rendered PDF's extracted text (`wrapped_lines` in
`check_pdf.py`) -- a source line that wraps onto two lines in the rendered
PDF fails this check, because the wrapped copy no longer matches the
markdown line verbatim. Keep code lines readable in the source, but do not
manually hard-wrap a line to make it fit a page width: the checker expects
each source line to survive as one indivisible line in the rendered
output, and a line broken by hand in the markdown is not the same line
`wrapped_lines` is looking for. If a real line is too long to fit,
`rendering.md`'s page-width contract, not a manual line break here, is
where that gets fixed.

## Phase 3 exit criteria

Do not move to Phase 4 until all of the following are true:

- the five fixed spine sections open the document, in order, each present
  even when the honest content is "there are no callers" or "no canonical
  form exists";
- the derived middle reflects the implementation's own structure, not a
  generic template;
- the three canonical inline-SVG roles -- `implementation-structure`,
  `execution-flow`, and `decision-landscape` -- each appear exactly once, with
  the metadata and numbered caption required by `diagrams.md`;
- every canonical and supplemental figure is followed by a cited
  interpretation, contains only relationships established in the visual or
  decision inventory, and replaces rather than duplicates an enumeration in
  prose;
- every load-bearing state machine, data layout, lifecycle, concurrency
  protocol, or algorithm-stage relationship that reads more clearly as a
  visual has a supplemental figure;
- every decision block uses the exact three markers, in order, at column
  zero, separated by blank lines so the parts render as three lines rather
  than one paragraph, closed by the next `**Decision.**` or the next `## `
  heading;
- every substantive claim carries one or more `[ID]` references, checked
  by one full read-through of the document, not only by
  `check_evidence.py`'s mechanical pass;
- every ledger entry in the notes file is written in the exact bullet
  grammar (`- [ID] ...`, one hyphen, one space, uppercase-first ID),
  checked by eye -- a near-miss bullet parses as prose, not as a malformed
  entry, so nothing mechanical will flag it;
- no bracketed all-uppercase text appears in prose except genuine ledger
  IDs;
- Improvements, Boundary note, Sources, and the generated Evidence ledger all
  exist in that order, with every improvement entry falsifiable; Sources is
  the final authored section, and `materialize-ledger` has projected the
  current notes into the terminal managed section without hand edits;
- every section heading is `## N. Title`, numbered sequentially with no
  gaps or repeats by discipline (checked by eye -- the checker only builds
  a set of numbers seen and does not notice a gap or a duplicate), and
  every cross-reference reads `section N` or `sections N and M` against a
  heading number that actually exists in that set (this part the checker
  does enforce).

A document that reads well but fails any of these is not ready for Phase
4 -- `check_pdf.py` and `check_evidence.py` exist because a document that
merely reads well is not the same thing as one whose every claim can be
checked.
