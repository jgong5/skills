# Phase 5: Verify

Phase 5 is the gate: `<stem>.pptx` is not finished until three independent
reviewers have read it and every definite finding is fixed or reported. The
build's warnings check what can be measured; these reviews check what a
reader sees. Each reviewer covers a different failure class and none
substitutes for another: the fact-checker cannot see a clipped label, the
visual reviewer cannot tell a wrong claim from a right one, and neither
reads the deck as the audience will.

## Render

Render the deck to a PDF with LibreOffice, then each page to an image with
poppler's `pdftoppm`:

    soffice --headless --convert-to pdf --outdir <out> <out>/<stem>.pptx
    mkdir -p <out>/render
    pdftoppm -r 110 -png <out>/<stem>.pdf <out>/render/slide

The binary may be installed as `libreoffice` rather than `soffice`. Before
rendering, check each declared font with `fc-list ':family=<font>'`; an
empty result means the render will substitute it.

Then extract the deck's text into `render/text.md`, one heading per slide
with its slide text and its notes. A `.pptx` is a zip: slide `n`'s text is
the `<a:t>` runs of `ppt/slides/slide<n>.xml`, and its notes those of
`ppt/notesSlides/notesSlide<n>.xml`. The fact-checker compares this text
with the code, and the reviewers need the notes, which the PDF does not
carry.

LibreOffice is not PowerPoint and can break a line differently. The images
are the closest view available, not the presenter's exact one; say so in the
report.

## The reviewer briefs

Dispatch the three reviewers in parallel, each as its own agent with only
the inputs its brief lists. **No reviewer receives the author's reasoning**:
not `outline.md`, not the conversation, not scratch notes, not an earlier
round's dispositions. A reviewer handed the reasoning checks the reasoning
instead of the deck, and agrees with it -- the deck is what the audience
gets, so the deck alone is what is reviewed.

### Fact-check reviewer

Inputs: `render/text.md`, the images, `plan.md`, `survey.md`, `demo/`, and
read access to the repository at the pin (`git show <pin>:<path>`, so a
working tree that has moved since does not matter).

Must not receive: `outline.md` or anything else of the author's reasoning.

It checks that every claim on a slide traces to the pinned code,
`survey.md`, or a `demo/` output; that every `path: symbol` citation
resolves at the pin and its excerpt is verbatim, with `...` elisions only;
that every number matches its source, and every step-through number matches
the replay output or is marked hand-derived in the notes; that every claim
about all or none of something holds for every item in the code; and that
the footer pin is the survey's pin.

### Visual reviewer

Inputs: the images, the declared fonts and which of them the render machine
lacks, the list of `noFitCheck` elements from Phase 4, and the list of
deckkit's warning kinds.

Must not receive: the code, `survey.md`, `plan.md`, `outline.md`, or the
notes. Its job is layout; content in hand pulls it into the other two
reviews, and a duplicate finding costs a duplicate spot-check.

It reports only what the build's checks cannot see: text clipped or
overflowing in the render despite a clean estimate, every `noFitCheck`
element, shapes or labels overlapping, arrows that miss the boxes they
connect, a highlighted code line that cannot be read, characters drawn as
empty boxes or in a substituted font, and a footer or slide number covered
by content. A fault deckkit already warns about is not reported again unless
the render contradicts the estimate.

### Narrative reviewer

Inputs: the images, `render/text.md`, `plan.md`, and `teaching.md`.

Must not receive: the code, `survey.md`, `demo/`, or `outline.md`. It reads
as a newcomer, and a newcomer has only the deck. A reviewer with the sources
fills each gap from them, as an expert does, and those gaps are what the
hard rules exist to find.

It walks the deck once per rule and cites the rule by ID:

- **R1.** For each mechanism, find the earlier slide where the running
  example fails without it. None, or only a "why" box, is a finding.
- **R2.** Each throughline in `plan.md` has its own slide before its first
  instance, and every instance names it.
- **R3.** A table on a slide whose content has a flow or structure that a
  diagram could show, or that a diagram already shows.
- **R4.** A principle that cannot be repeated as one sentence, or whose
  exception is missing or on another slide.
- **R5.** The first slide where each symbol, variable, and term appears
  explains it; a later explanation is a finding on the first slide.
- **R6.** Every "all", "every", "always", and "never": is it plausible for
  every item, or does the deck itself show an exception?
- **R7.** An example that is not from `plan.md`'s main line or scenarios.
- **R8.** A slide teaching two things, or a code excerpt over about 15
  lines or without a citation.
- **R9.** A claim on a slide stated as settled that the notes mark as open
  or hand-derived.

### Finding format

Every reviewer reports each finding as:

    slide: <n>
    quote: <the exact text on the slide, or the element for a visual finding>
    basis: <fact: the path: symbol at the pin, survey.md entry, or demo file;
            visual: the image and what it shows; narrative: R<n> and how the
            slide breaks it>
    fix: <the proposed change>
    certainty: definite | possible

`quote` lets the author find the text without guessing which part of the
slide is meant. `basis` is what the spot-check reads. `definite` means the
basis shows the slide is wrong; `possible` means the reviewer suspects it
and the basis does not settle it.

## Spot-check, then fix

Before fixing a finding, check its basis yourself: open the cited code at
the pin, the survey entry, the replay output, or the image. Reviewers are
independent and can be wrong, and a fix applied on a wrong basis puts an
error into a deck that was right.

- A definite finding whose basis holds is fixed.
- A finding whose basis does not hold is rejected, with what the check
  found.
- A possible finding is settled by the lookup when it can be, and becomes
  definite or rejected. When it cannot be, the claim moves off the slide
  into the notes as an open question (`teaching.md`, R9).

Fix in `build.js`, rebuild, fix every new deckkit warning (`building.md`),
and render again.

## Rounds and the stop rule

Round 1 reviews the whole deck. Each later round reviews only the slides
changed in the round before, the slides adjacent to each, and any slide
whose outline `failure` field points at a changed slide: a change can break
a neighbour that relied on it. Reviewers still receive the whole deck, so
they read the changed slides in context, but report findings only on the
slides named.

Stop at the first round with no definite finding that survives the
spot-check, or after round 3. A deck still producing definite findings after
three rounds has a fault that fixing slides one at a time does not converge
on; report every finding still open rather than starting a fourth round.

## The `reviews/` record

Write `reviews/round-<k>.md` for each round: the slides reviewed, each
reviewer's findings verbatim, and each finding's disposition -- fixed (what
changed), rejected (what the spot-check found), or open (why). When slides
were added or removed, record the old and new numbers. Phase 6 adds its
feedback rounds to the same directory (`revision.md`).

The record is the deck's audit trail: a later reader can see what was
checked, by whom, and why a slide says what it says.

## Degradation

Each row is reported in the final report, never worked around silently.

| Condition | What Verify does |
|---|---|
| No LibreOffice or no poppler | Build and fix the warnings, extract `render/text.md`, and run the fact-check and narrative reviews on it alone. Skip the visual review and say so. |
| A declared font missing on the render machine | Render anyway. Tell the visual reviewer which font, and say in the report that the images show a substitute. |
| No subagents | Run the three reviews in sequence, each against its own brief only, and report them as not independent: the author already holds the reasoning the briefs withhold. |
| Not a git repository | The fact-checker reads the code at the pinned path as it is now; the report says the citations have no version baseline. |
| Step-through hand-derived | The fact-checker re-derives each hand-derived number and checks that its notes mark it so. |
