# Phase 4: Write

Phase 4 turns the four inventories into `<stem>_architecture.md`. Nothing new
is discovered here -- a sentence or an edge that needs evidence the earlier
phases did not produce is a sign to go back, not to write around. Two scripts
read this document mechanically in Phase 6, `check_pdf.py` and
`check_evidence.py`, and every contract they enforce is written here beside
the rule it serves, because a contract that lives only in a regex is a
contract nobody writing prose can see.

## Citing evidence in prose

Cite with the ledger ID in brackets: "the scheduler is the only writer of the
queue [C1]." String several together when a sentence rests on more than one
(`[C3][K7]`). Every claim a skeptical peer could answer "says who?" to carries
one; connective prose does not need a decorative citation.

An unused ledger entry is fine -- the inventories turn up more than the report
uses, and nothing flags a `[C9]` the prose never mentions. The reverse is
flagged: a `[C9]` the prose cites and the ledger does not define. Nothing
mechanical catches the real risk, a claim that should have carried a citation
and did not. That is caught by reading the document start to finish once,
asking of every sentence whether it needs one.

**Never put an acronym in square brackets.** `check_evidence.py` scans every
non-fenced line for `[BRACKETED-UPPERCASE]` and treats each match as a ledger
citation, so "the [GPU] scheduler" or "a [TODO] left behind" fails Phase 6 as
a reference to an undefined ledger ID. This report is denser in acronyms than
most documents; write them bare in prose, and reserve square brackets for
ledger IDs and footnote markers.

## Abbreviations and the Notes chapter

Every abbreviation is spelled out and footnoted at its first appearance in
prose, in exactly this shape, and never spelled out again:

```markdown
The scheduler holds the GIL (Global Interpreter Lock)[^gil] across the copy.

[^gil]: CPython's interpreter-wide mutex. Only one thread executes Python
    bytecode at a time, so a CPU-bound section serialises every other thread
    in the process regardless of core count.
```

`check_pdf.py` enforces this: a run of two or more uppercase letters or
digits, or a slashed pair such as `I/O`, must be followed at its first prose
occurrence by ` (Expansion)[^tag]`, the expansion's word initials must cover
the abbreviation, no later occurrence may be expanded again, and every `[^tag]`
must be defined exactly once and used. Abbreviations inside fenced code,
inline code, figure markup, footnote text, and the generated ledger are
exempt -- those are not the author introducing a term to a reader.

Two things follow from how this renders. Chrome's print engine has no support
for paged-media footnotes, so pandoc's footnotes become an endnote chapter at
the back of the PDF rather than sitting at the foot of each page. That makes
the parenthetical expansion the part the reader actually reads inline, and the
note the part they consult only when they want the mechanism. Write the
expansion to carry the term and the note to carry one or two sentences of
mechanism worth the trip -- a note that restates the expansion has cost the
reader a page turn for nothing.

## Fixed spine

Nine numbered sections, titled verbatim, in this order. `check_pdf.py` matches
the first seven titles character for character; changing one means changing
`SPINE` in that file at the same time.

```markdown
## 1. Architectural deconstruction
## 2. Key abstractions and data models
## 3. Execution lifecycle and data flow
## 4. Trade-off analysis
## 5. System constraints and vulnerabilities
## 6. Alternative paradigms
## 7. Guided exploration
## 8. Sources
## 9. Evidence ledger
```

**Section 1** opens with the `**Boundary.**` block -- one paragraph at column
zero, exactly one in the document, naming what was read and every component
Phase 1 recorded as a boundary edge, with its reason. Then the paradigm per
layer, each with the structure that witnesses it and the forcing function that
produced it, and the seam where one layer's assumptions give way to the next.
Figure `system-decomposition` carries the shape; the prose carries the
consequence.

**Section 2** walks the contract inventory: for each major component, the
abstraction it presents and the precise shape of what crosses its seams --
fields, dtypes, node types, template slots, envelope keys -- plus who
allocates, who owns it afterward, and what leaks. Answer the decoupling
question **seam by seam**, against the cut test from `<skill-dir>/survey.md`:
a global verdict that the contracts are "cleanly decoupled" is an adjective
the reader cannot check, while "this seam cuts, that one does not because the
caller must call `warmup()` first [K4]" is a finding. Figure `contract-map`.

**Section 3** follows the traced loop, named, from entry to exit: what runs
where, what state changes and who owns it, what is allocated and what frees
it, which seam each hop crosses, and where it waits. Include the failure path
Phase 2 followed. Figure `execution-lifecycle`.

**Section 4** is decision blocks, in the shape below, one per decision the
inventory kept. Figure `tradeoff-landscape`.

**Section 5** is the constraint inventory, each entry naming the mechanism at
`path:line` and the trigger that makes it bite, including the change-
amplification counts. A `blocking-path` figure is usually earned here.

**Section 6** is one or two whole-system alternatives, each with the condition
under which it wins. An `alternative-paradigm` figure is usually earned here.

**Section 7** is 2 to 4 questions, written as list items each ending in a
question mark -- `check_pdf.py` counts exactly that, bounded by its
`MIN_QUESTIONS` and `MAX_QUESTIONS`. Nothing else goes in this
section; a summary paragraph before the questions dilutes the close.

**Section 8** lists every external reference used anywhere in the document --
specifications, papers, upstream documentation -- once, so a reader does not
hunt back through the prose for a link.

**Section 9** is generated. Never type or edit it.

## Diagrams

Read `<skill-dir>/diagrams.md` before drafting the body. The report is
diagram-first: the four required figures carry the system's shape and the
prose carries the consequence, rather than reading boxes and arrows aloud.

## Decision blocks

Exactly three parts, labels verbatim, each starting its own line, separated by
blank lines:

```markdown
**Decision.** <what the code does>

**Alternatives.** <one to three realistic other choices>

**Why this one.** <the deciding constraint, cited, plus what it costs and when>
```

The blank lines are a rendering rule, not a parser rule, and they are the one
part Phase 6 cannot catch: `check_pdf.py` reads the markdown, so three
adjacent lines pass the checker and then render as one run-on paragraph with
three bold labels buried mid-sentence -- which is exactly the structure the
block exists to make visible.

The literal markers, their wording, and their order are a machine-readable
contract with `check_pdf.py`'s `DECISION_MARKERS`. Concretely:

- Every marker begins at column zero. Indented inside a list item or a
  blockquote, it does not match and the block is invisible to the checker.
- The three appear in exactly this order. Swapping two is reported as parts
  out of order, not silently accepted.
- `**Decision.**` opens a block and closes whatever was open before it,
  missing parts and all; a `## ` heading also closes one.
- An `**Alternatives.**` or `**Why this one.**` with no open block before it
  is dropped rather than reported. Always open with `**Decision.**`.
- Do not reword a label, even when the reworded version reads better. A label
  the regex misses makes the whole block invisible to Phase 6.

At least one decision block must exist; a trade-off analysis that states no
decision is not one.

## Pseudocode, when the traced loop earns it

A `pseudocode` block is optional and belongs only in section 3, when the
control flow itself is the thing worth teaching and prose would take a page to
say it. Fence with the literal info string `pseudocode`; the first non-blank
line is `procedure Name(args):` or `refine Name(args):`; a block runs to at
most 20 steps, and a longer one is refined into a named block that another
block calls. `check_pdf.py` enforces the header, the step limit, unique names,
and that every `refine` block is actually called. A loop whose control flow is
one delegating call earns no block, and manufacturing one to fill the section
is the failure this skill exists to avoid.

## Headings, cross-references, and code

Number every section `## N. Title` from 1, with no gap and no repeat --
`check_pdf.py` checks the whole sequence, so a duplicated or skipped number is
a Phase 6 failure, not just a reader's annoyance. Phrase a cross-reference as
`section N` or `sections N and M`, which is what `XREF_RE` resolves against
the headings that exist; "as discussed earlier" is invisible to the check and
is not a substitute when precision matters.

Every non-blank line inside a fenced code block is checked, modulo
whitespace, against the rendered PDF's extracted text: a line that wraps in
the PDF comes back split and fails. Keep excerpts short and honest, but never
hard-wrap a line by hand to make it fit -- the checker expects each source
line to survive as one indivisible line, and `<skill-dir>/rendering.md`'s
page-width arithmetic is where a genuinely long line gets handled.

## Generate the Evidence ledger

After all authored prose and all notes are final, run through the project's
command wrapper:

    <skill-dir>/check_evidence.py materialize-ledger \
        <stem>_architecture.md <stem>_architecture.notes.md

This creates or replaces section 9 deterministically and rewrites each plain
`[C1]` in the prose into the anchor that links it to its definition and back:

    <a id="ref-C1-1" href="#evidence-C1">[C1]</a>

Keep typing the plain `[C1]`. The rewrite is idempotent and reversible -- it
strips the previous anchors before generating new ones -- so edit a linked
sentence as though the marks were still plain text and rerun the command. If
the prose or the notes change afterward, rerun it before Render;
`check_evidence.py verify` rejects a missing, stale, reordered, or edited
projection, including a citation added or deleted since the links were last
generated. The notes file stays the single authored source of truth.

## Phase 4 exit criteria

Do not move to Phase 5 until all of the following are true:

- the nine spine sections are present, titled verbatim, numbered without gap
  or repeat;
- the single `**Boundary.**` block sits in section 1 and names every excluded
  component with its reason;
- the four required figures are present, each followed by a cited
  interpretation, each containing only relationships an inventory established;
- section 2 answers the decoupling question seam by seam, never globally;
- section 5 contains no claim whose only support is a fact about the language,
  the runtime, or the hardware;
- section 6's alternatives each state the condition under which they win;
- section 7 is two to four questions and nothing else;
- every abbreviation is expanded and footnoted at first use, exactly once, and
  no acronym appears in square brackets anywhere in prose;
- at least one complete decision block exists, every marker at column zero,
  separated by blank lines;
- `materialize-ledger` has been run after the last edit to prose or notes.
