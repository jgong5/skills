# Phase 5: Verify

Phase 5 is the gate: `<stem>_study.pdf` and `<stem>_study.md` do not count as
finished until all three passes below are clean. Each pass catches a
different failure class, and none of the three substitutes for another --
`check_pdf.py` cannot tell a true sentence from a false one, `check_evidence.py`
cannot tell a well-laid-out page from a wrapped one, and neither script can
read the document the way a skeptical human does.

## Preflight

Pass 1 needs `poppler-utils` already installed -- `pdftotext`, `pdffonts`,
and `pdfinfo`, plus `pdftoppm` for the sample-page rasterization step below.
Unlike `make_pdf.py`'s Chrome/pandoc/websockets checks in Phase 4,
`check_pdf.py` does not probe for these itself; a missing one surfaces only
as a raw, uncaught error naming the binary it tried to run. Treat that the
same as a `make_pdf.py` preflight failure: stop and name the specific
missing tool and the `poppler-utils` package that provides it, rather than
working around it or reporting Pass 1 clean without having actually run it.

## Pass 1: Mechanical PDF checks

Run `check_pdf.py` through the project's command wrapper, never a bare
`python3`:

    <skill-dir>/check_pdf.py <stem>_study.pdf <stem>_study.md

This checks, over every page: every font `pdffonts` reports is embedded;
every code line in the markdown survives verbatim (mod whitespace) in the
`pdftotext -layout` extraction, so a line that wrapped in the rendered PDF
is caught; every "section N" / "sections N and M" cross-reference resolves
to a `## N.` heading that exists; every `**Decision.**` /
`**Alternatives.**` / `**Why this one.**` block is complete and in order;
every `pseudocode` block opens with a `procedure` or `refine` header, has a
name used once, stays inside the step limit, and -- when it is a `refine`
block -- is called by another block; and `pdfinfo` reports a page count.
It exits 0 and prints a one-line "clean: N pages, all fonts embedded"
summary followed by a sample-page table; it exits 1 with one `PROBLEM:`
line per failed category on stderr and skips the table.

`check_pdf.py`'s fence detection is a simple toggle: any line that opens
with ` ``` ` or `~~~` flips an in-fence flag, without remembering which of
the two markers actually opened the block. Mixing fence styles inside one
study document (opening with ` ``` ` and later "closing" with `~~~`, or vice
versa) can therefore mis-scope which lines the checker treats as code. This
has not been a problem in practice because every code excerpt in a study
document uses triple backticks; keep doing that, and the checker's fence
handling never has anything to disagree with.

When the run is clean, rasterize every page number the sample-page table
reports and look at each one:

    pdftoppm -f <N> -l <N> -png <stem>_study.pdf page

`check_pdf.py` reports the title, contents, every required diagram page, the
widest code block, a table, a dense prose page, and the last page because it
already has the extracted text and works these out itself; do not hunt for
them by hand. For each rasterized page, look specifically for what a
mechanical check cannot see: a title page with the right title, a contents page
whose entries look complete, the widest code block rendered without visible
overflow past the margin, a table with readable columns, a dense prose page
with normal line breaks, and a last page that actually looks like an ending
(Sources, not a mid-sentence cutoff).

Inspect every diagram page for clipped nodes, edges, labels, or arrowheads;
type too small to read; a figure split across pages; reliance on color without
a line-style or label distinction; and a caption separated from its figure.
Read the interpretation beside it too: it must explain the takeaway and cite
the visual assertions rather than repeat each label in sentence form.

The table's `widest_code` entry is about width only, and width says nothing
about height: the page carrying the longest code *line* is usually not the
page carrying the tallest code *block*, so sampling `widest_code` does not
cover a block too tall for the page. Look deliberately for that as well --
rasterize the pages around every long code block and check for a block
broken across a page boundary, or pushed whole to the next page leaving an
obvious gap behind. That is a Phase 4 classification finding, the page-tall
class in `rendering.md`, and the fix is a shorter excerpt or a deliberate
split in the markdown, never a smaller code font.

## Pass 2: Evidence and integrity checks

Run `check_evidence.py verify` with the repository root and the output
directory it was given at the start of the study, and pass `--snapshot`
only when the repository under study has no version control:

    <skill-dir>/check_evidence.py verify <stem>_study.md <stem>_study.notes.md \
        --repo-root ROOT --output-dir OUT [--snapshot FILE]

This is the ledger discipline made mechanical: the terminal generated
Evidence ledger exists and exactly matches the authoritative notes file, and
every prose mark carries its current cross-link, so a reader can resolve every
inline ID inside the Markdown or PDF without opening that companion file;
every entry parses in the exact grammar with a recognized
evidence class; every `cite:` file citation
resolves inside the repository with its backticked anchor still on the
cited line; every `derive:` names ledger IDs that exist, shows its reasoning
after `--`, and takes part in no cycle; every `measure:` points at a script
and captured output that both exist beside an `ENV.md` and an approved
`PLAN.md` line; every `[ID]` the prose cites exists in the ledger; and the
repository under study came out as it went in, as far as the mechanism it
has can see.

That last check has two different mechanisms depending on how the
repository is tracked, they are not interchangeable, and they do not see the
same set of files:

- **A git work tree.** `check_evidence.py` runs `git status` itself and
  requires every entry to be untracked (`??`) and inside the output
  directory; a tracked modification anywhere, or an untracked file outside
  the output directory, is a `PROBLEM:` line. If `--repo-root` names a
  subdirectory of a larger repository, this check still asks git for the
  whole repository's status, not just that subdirectory -- an unrelated
  untracked file elsewhere in the same monorepo is reported here too. That
  is the safe direction to err in, but before assuming the study itself
  broke something, check whether the flagged path is actually related to
  the subdirectory under study. The limit of this check is what `git status`
  itself reports: paths excluded by `.gitignore` are invisible to it, so a
  write into an ignored path -- `__pycache__/`, a build directory, a tool
  cache -- inside the repository under study passes without a word. The
  checker deliberately does not compensate with a scan of ignored files,
  because Phase 1 recorded no baseline of which ignored paths existed
  beforehand and an unbaselined scan cannot tell a file this run created
  from one that was already there. Prevention is where that gap is closed:
  `experiments.md` requires every experiment to run with its language's
  cache and artifact writes suppressed. When reporting Pass 2 clean, report
  what was actually proved -- no tracked change, and no untracked,
  unignored file outside the output directory -- rather than describing the
  repository as byte-for-byte unchanged.
- **A repository with no version control.** There is no `git status` to
  ask, so `--snapshot` compares the tree against the `<stem>_study.integrity.json`
  baseline Phase 1 wrote with `check_evidence.py snapshot`. Pass `--snapshot`
  only in this case; it is not a stronger check to layer on top of a git
  repository "just in case" -- the snapshot walk does not exclude `.git`,
  and pointing it at an actual git work tree produces spurious failures
  from ordinary index churn. The snapshot itself records file size and
  mtime for every file outside the output directory, plus a sha256 hash for
  every cited file, which means a content-identical rewrite -- the same
  bytes written back with a new mtime, as a formatter or a re-link step can
  do without changing a single byte -- still fails verification with
  `"<path>: mtime changed"`. That is the check working as designed, not a
  false positive to explain away: the fix is to re-run `snapshot` and
  re-baseline from the current state, never to loosen the check or ignore
  the finding.

`check_evidence.py` exits 0 and prints "clean: N ledger entries verified"
only when every one of the checks above passes; otherwise it exits 1 with
one `PROBLEM:` line per finding on stderr, and Pass 2 is not clean until
every line is addressed.

## Pass 3: Manual read-through

Read `<stem>_study.md` once, start to finish, the way a skeptical reader
would, specifically for two things neither script can check: missing citations
and unsupported assertions. `check_pdf.py` and `check_evidence.py`
between them catch a bad cross-reference, a bad ledger entry, and an
unsourced `[ID]`, but neither can distinguish a claim that genuinely needed
a citation and did not get one from ordinary connective prose ("first,"
"this means," "as a result") that never needed one -- that distinction is
exactly what this pass exists to make. Read every sentence and ask whether
a skeptical reader could reasonably ask "says who?" about it; if so, it
needs a digit-suffixed ledger reference such as `[C1]`, `[D2]`, or `[M3]`,
and it is a Pass 3 finding if it
does not have one, mechanically clean ledger or not.

Treat each figure as prose with geometry. Trace every important node, edge,
transition, and comparison to its adjacent cited interpretation and the ledger
entries behind that interpretation. Then ask whether the figure teaches a
relationship more directly than the prose; a decorative visual or a paragraph
that simply reads the diagram aloud is a Phase 3 finding even when every
mechanical check passes.

Read each pseudocode block the same way. The top level should read as the
algorithm itself, in the domain's vocabulary and at one altitude, not as the
source with its syntax filed off; a block that could be swapped for the
excerpt beside it without loss is a Phase 3 finding. Check that the paragraph
after each block carries the ledger IDs for what the block asserts -- an ID
typed inside the fence is invisible to `check_evidence.py` and supports
nothing -- and that a step no ledger entry covers goes back to Phase 1's step
trace rather than being talked around.

Do not turn this pass into a mechanical check of the fixed-spine headings
from `writing.md`. A section that honestly says "there are no callers" or
"no canonical form exists" is not a defect -- the spine's five sections
legitimately degrade to a sentence when the honest content is that short,
and flagging every thin section as a finding would push authors toward
padding prose to satisfy a read-through instead of stating a true, short
fact.

## Route findings to their source

A finding from any of the three passes is not fixed by re-rendering and
re-checking until it has been classified. Fix the document at its source,
not at the pass that happened to catch it:

- A citation, derivation, experiment, or integrity finding -- a broken
  anchor, an unapproved measurement, a cycle, an untracked file outside the
  output directory -- returns to `Phase 1 or Phase 2`: the ledger and the
  decision inventory are where that evidence was supposed to come from, and
  a finding here means something was asserted before it was actually
  established.
- A render, wrapping, visual, or cross-reference finding -- a code line
  that wrapped, a page that looks visually wrong, a "section N" pointing at
  a heading that does not exist, a pseudocode block that overran the step
  limit or transliterated its source -- returns to `Phase 3 or tutorial.css`:
  either the markdown itself needs to change (a shorter excerpt, a
  corrected section number, a fixed decision block), or `tutorial.css`'s
  code-sizing arithmetic needs to change per `rendering.md`, but not both
  guessed at once.

Editing the prose to agree with a bad ledger entry launders the error
instead of fixing it -- if a citation is wrong, correct the ledger and
re-derive whatever the prose said from the corrected evidence, do not edit
the sentence to match whatever the broken citation happened to say. After
every fix, rerun all three passes, not only the one that reported the
finding: a fix to the markdown can move a heading number that Pass 1 was
not complaining about yet, and a fix to the ledger can change what Pass 3's
read-through needs to re-examine.

## Phase 5 exit criteria

Do not call the study finished until all of the following are true:

- Pass 1 (`check_pdf.py`) exits clean, including its checks that every
  generated evidence definition survived PDF extraction and that every mark
  and back-reference became a working PDF link, and every sample page it
  reported -- including the Evidence ledger page -- has actually been
  rasterized and looked at;
- Pass 2 (`check_evidence.py verify`) exits clean, using `--snapshot` only
  when the repository under study is not a git work tree, and with no
  outstanding "mtime changed" or "tracked change" findings papered over
  rather than resolved;
- Pass 3's manual read-through has been performed start to finish, with
  every claim a skeptical reader would question either cited, derived, or
  named as an open question, and with no thin-but-honest fixed-spine
  section flagged as though it were a defect;
- every finding surfaced by any pass has been routed to its actual source
  (`Phase 1 or Phase 2`, or `Phase 3 or tutorial.css`) and fixed there, and
  all three passes were rerun clean after the fix, not just the pass that
  first caught it.

A study that passes Pass 1 and Pass 2 but skips Pass 3 is not verified --
mechanical cleanliness is necessary and it is not the same thing as a
document whose every claim can survive a skeptical reading.
