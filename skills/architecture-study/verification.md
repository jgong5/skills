# Phase 6: Verify

Phase 6 is the gate. Three passes: two mechanical, one by eye. The mechanical
passes catch what a regex can see -- a wrapped line, a broken reference, an
unexpanded abbreviation, a moved citation anchor. The read-through catches
what only a reader can: a sentence that is fluent, well-cited, and describes a
system other than this one.

No finding is fixed here. Every one routes back to the phase that caused it.

## Preflight

Pass 1 shells out to `poppler-utils` by name: `pdftotext`, `pdffonts`,
`pdfinfo`, and -- for the sample-page rasterization in Pass 3 -- `pdftoppm`.
If one is missing, stop and name the specific tool and the package that
provides it. Do not skip the pass or report it clean without having run it.

## Pass 1: mechanical PDF checks

Through the project's command wrapper:

    <skill-dir>/check_pdf.py <stem>_architecture.pdf <stem>_architecture.md

It checks font embedding, code-line survival, the seven-section spine, the
single `**Boundary.**` block, cross-references, decision blocks, the
guided-exploration close, the abbreviation and footnote contract, the four
required figures and their metadata, the rendered evidence definitions and
links, and the page count. Exit 0 prints `clean: N pages` plus a sample-page
table; exit 1 prints `PROBLEM:` lines on stderr.

Read the problems as diagnoses, not as chores:

- **wrapped code line** -- a width problem. Route to Phase 5's classification,
  which decides between excerpting, resizing, and rewrapping.
- **spine problem** -- a heading was retitled, misnumbered, or dropped. Route
  to Phase 4. The titles are matched character for character on purpose.
- **boundary problem** -- the scope is undisclosed or the block drifted out of
  section 1. Route to Phase 4 if the block moved, Phase 1 if the boundary was
  never actually declared.
- **abbreviation problem** -- route to Phase 4. Watch for the expansion that
  does not spell out its abbreviation: that is usually a genuine error, an
  acronym expanded to the wrong words.
- **decision block problem** -- a missing block means section 4 states no
  decision, which routes to Phase 3, not Phase 4. An incomplete block routes
  to Phase 4.
- **guided-exploration problem** -- too few or too many questions. Route to
  Phase 3, where the questions were collected.
- **diagram contract or render problem** -- missing metadata routes to Phase
  4; text that did not survive extraction usually means the label was drawn
  outside the `viewBox` or shrunk past legibility, which routes to Phase 5.
- **evidence render or link problem** -- the ledger projection is stale.
  Rerun `materialize-ledger` and render again.

## Pass 2: evidence and integrity checks

Through the same wrapper:

    <skill-dir>/check_evidence.py verify \
        <stem>_architecture.md <stem>_architecture.notes.md \
        --repo-root <repo-root> --output-dir <output-dir>

Add `--snapshot <stem>_architecture.integrity.json` when the system under
study is not in a git work tree.

This checks that every ledger entry parses, that IDs are unique, that every
`cite:` resolves inside the repository with its anchor still on the cited
line, that every `derive:` names existing IDs and forms no cycle, that every
`[ID]` in the prose is defined, that the generated ledger chapter matches the
notes, and that nothing outside the output directory changed.

Two failures deserve particular attention:

- **a moved anchor** is reported with the line it now sits on. That is not a
  formatting nit: the file changed under the study, and the claim built on
  that line may no longer be true. Route to Phase 1 or Phase 2 and reread,
  rather than editing the line number and moving on.
- **a modified file outside the output directory** means the read-only
  invariant broke. Find what wrote, and say so plainly in the final report to
  the user. In a work tree the check sees exactly what `git status` sees, so a
  `.gitignore`-matched cache write passes silently -- which is a reason to run
  nothing that writes, not a reason to trust the check more than it deserves.

## Pass 3: read the document

Six sweeps, each with a different question. Do them separately; folding them
together is how a sweep gets skipped.

1. **The witness sweep.** For every paradigm, constraint, and coupling the
   report names, find its ledger entry, open the cited file, and confirm the
   structure is actually there. This is the single most valuable thing in
   Phase 6, and it is the only defence against the failure this whole skill is
   built around: a review of the system the code resembles.
2. **The genre sweep.** Read section 3 alone and ask of each paragraph
   whether it could have been written without reading the code. A lifecycle
   assembled from familiarity with the genre reads exactly like one assembled
   from the source. Any paragraph that passes this test without a `path:line`
   behind it goes back to Phase 2.
3. **The adjective sweep.** Search the prose for "clean", "cleanly",
   "loosely coupled", "tightly coupled", "elegant", "robust", "scalable",
   "simply", and "well-". Each one either has something checkable attached to
   it -- a seam that cuts, a count of components a change touches, a trigger
   -- or it comes out. An adjective is where a claim goes when it could not
   find evidence.
4. **The altitude sweep.** Anything explaining a language feature or a
   standard-library idiom is below the reader and comes out. Anything that
   stops at a summary where the mechanism was the point is above them and gets
   pushed down one level.
5. **The close sweep.** Read section 7's questions and ask, for each, whether
   the reader can answer it and the report cannot. A question the report
   already answers is a quiz; a question nobody can answer is rhetoric. Both
   come out, and both route to Phase 3.
6. **The page sweep.** Rasterize every page `check_pdf.py`'s sample table
   named and look at it:

       pdftoppm -f N -l N -png <stem>_architecture.pdf page

   Look for figures broken across pages, labels colliding, a table spilling
   the measure, a code block split, an orphaned heading, and whether each
   figure still reads in grayscale. Also open the Notes chapter and confirm it
   is not the first thing a reader would need but the last.

## Route findings to their source

| Finding | Phase |
| --- | --- |
| a claim has no witness, or the witness does not show what was claimed | 1 or 2 |
| a lifecycle step cannot be traced to a `path:line` | 2 |
| a component's internals are described but were never read | 1 |
| a decision has no realistic alternative, or the alternative is a strawman | 3 |
| a trade-off names no condition under which the cost bites | 3 |
| section 5 rests on a fact about the language, runtime, or hardware | 2 |
| section 6 states a preference rather than a condition | 3 |
| a question the report already answers | 3 |
| an adjective standing in for a measurement | 3 |
| a spine, decision-block, abbreviation, figure-metadata, or citation-syntax defect | 4 |
| a wrapped line, an over-tall block, a crowded figure | 5 |
| a stale ledger projection | rerun `materialize-ledger`, then 5 |

Nothing is fixed at the pass that caught it. A wrapped code line fixed by
shrinking the font in Phase 6 skips the classification that would have shown
the excerpt was simply too long; a missing witness fixed by deleting the
citation leaves the claim standing with nothing under it.

## Phase 6 exit criteria

Do not report the study finished until all of the following are true:

- `check_pdf.py` exits clean;
- `check_evidence.py verify` exits clean;
- all six read-through sweeps have been done, separately;
- every page the sample table named has been rasterized and looked at;
- every finding has been routed to its own phase and the affected passes rerun
  from there;
- no file that existed before this run started has been changed or deleted,
  and any exception is stated plainly to the user rather than left in the
  checker's output.
