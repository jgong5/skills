# Phase 1: Analyze

Phase 1 turns "study this implementation" into a resolved boundary, a mapped
contract, and the first entries of a claim ledger. Nothing produced here is
prose yet -- the study document does not exist until Phase 3. What Phase 1
produces is the evidence that Phase 3 is allowed to cite.

## Safety preflight

Stop and ask, rather than guess, in two situations:

- The entry point is ambiguous. "The queue implementation" in a repo with
  three queue-shaped classes, or a bare function name that resolves to
  several files, is not something to pick for the user. Ask which one.
- The code under study is generated, vendored, or minified: paths under
  `vendor/`, `third_party/`, `node_modules/`, `*.min.*`, or a file carrying a
  "generated" / "do not edit" header. A study of code nobody hand-wrote has no
  design decisions to recover and no history worth reading -- it produces
  citations to something no one will read again. Stop instead of writing a
  study nobody asked for.

Both are stops, not warnings logged and worked around. The rest of the
pipeline assumes the entry point is real, singular, and hand-written.

## Resolve the entry point and output directory

Resolve `<stem>` -- the name the rest of the pipeline hangs every output off
of -- and every output path (`<stem>_study.md`, `<stem>_study.notes.md`,
`<stem>_study.integrity.json`, the experiments directory) before creating
anything.

The output directory must be strictly inside the repository root, never the
repository root itself. `SKILL.md` resolves it by walking up to the nearest
ancestor `docs/`, falling back to the entry-point file's own directory; that
fallback is only usable when the entry point lives in a subdirectory. An
entry point sitting at the repository root with no ancestor `docs/` has no
valid fallback, and the answer is to stop and ask the user which
subdirectory to write into -- not to create `docs/` on their behalf, and not
to write to the root. `check_evidence.py` rejects `--output-dir` equal to
`--repo-root` in both `snapshot` and `verify`, and it is right to: if the
output directory were the root, every file in the repository would count as
"inside the output directory" and Phase 5's no-modification check would
report clean no matter what changed.

Fail if any target output file already exists. This skill may create files
but never overwrite them: an existing file with one of these names means
either a prior run that should be resumed or reviewed by a human, or a name
collision with something unrelated, and either way silently clobbering it
throws away evidence the skill did not produce. Resolving every path up front
also means the failure happens before any work is done, not after Phase 1 has
already spent effort tracing a boundary that turns out to collide on output.

## Declare the study boundary

An honest boundary is narrower than "the whole call graph." An entry point
that pulls in a framework, a large shared utility module, or a generic
container type does not get the same close reading as the code the study is
actually about -- tracing all of it would either take forever or, more
likely, get shallow and unreliable exactly where it matters least.

Declare a narrower boundary instead: the entry point, its direct
implementation, and the collaborators whose behavior actually shapes the
decisions under study. Preserve every component pushed outside that boundary
for the final Boundary note in the study document, so a reader can tell what
was deliberately excluded (and why) from what was simply missed. A boundary
that is honest about its edges is more useful than one that claims coverage
it does not have.

## Read contract, tests, callers, and callees

Before any claim goes in the ledger, read:

- the signature, docstring, and tests of the code under study -- the tests
  are often the most precise statement of the contract that exists;
- every in-repo caller, so the study reflects how the code is actually used,
  not only how it could theoretically be used;
- the nearest public API path from an external caller down to the entry
  point, so the study can place the code in context;
- direct dependencies -- what the code under study calls, not what those
  calls call;
- state and invariants the code establishes or relies on;
- relevant history with `git blame` and `git log -L <start>,<end>:<file>`
  when the repository has git history available. History often carries the
  "why" that the current code alone does not -- a comment removed three
  commits ago, a revert, a commit message citing a bug. Skip this only when
  the repository is not a git work tree, or history is genuinely unavailable
  (a shallow clone, a squashed import); do not skip it because it is
  inconvenient.

## Build the comprehension ledger

Start `<stem>_study.notes.md` in the parser's exact grammar, because
`check_evidence.py` reads this file mechanically in Phase 5 and cannot tell a
true claim from a false one, only a sourced one from an unsourced one. Every
entry has the shape:

```
- [ID] <claim>. <cite|derive|measure>: <source>
```

Use `[C1]`, `[C2]`, and so on for IDs, one ledger per study. A file claim
carries a `path:line` or `path:line-line` citation plus a verbatim,
backticked anchor -- the exact substring of the cited line(s), so a citation
can be checked mechanically instead of trusted on the honor system:

```
- [C1] The queue is a deque, not a list. cite: bfs.py:12 `queue = deque()`
```

Ledger IDs must end in a digit (`C1`, `PERF3`), not stop at a bare word
(`PERF`, `QUEUE`). The regex a derivation uses to find IDs inside its own
`derive: C1, C3 -- ...` source only matches an ID ending in a digit; an ID
that does not end in a digit parses fine as its own ledger entry but can
never be referenced from a derivation, and `check_evidence.py` now rejects
such an ID outright at parse time with a message asking for a digit suffix.
Number every ID from the start so this never comes up.

Bracketed, all-uppercase text in prose collides with this same citation
syntax. Once Phase 3 writes the study document, the evidence checker scans
every line outside a fenced code block for a `[BRACKETED-UPPERCASE]` pattern
and treats it as a reference to a ledger entry with that name -- whether or
not the author meant it as one. Writing "the [CPU] scheduler" or "a [TODO]
left in the code" produces a spurious "prose references unknown ledger id"
failure, because `[CPU]` and `[TODO]` read exactly like ledger IDs to the
checker. Reserve bracketed all-uppercase text for ledger IDs only; spell
acronyms out in running prose ("the CPU scheduler") or put them inside a
fenced code block if they must appear bracketed.

Include the literal sentence `Cite, derive, measure, or omit.` in the notes
file -- it is the rule the rest of the pipeline enforces mechanically, not
just a style preference. State plainly that the skill
`modifies or deletes nothing` in the repository under study: every artifact
this pipeline produces lives in the output directory, and anything that
cannot be sourced by one of the three evidence classes belongs in the
Boundary note, not typed into the prose as an assertion.

## Establish repository integrity

The study is a read-only act. Phase 5 checks that mechanically, but the
baseline for that proof is established here, before any output exists.

For a git work tree: require a clean baseline before producing any skill
outputs -- `git status` shows nothing tracked as modified, and any
pre-existing untracked files are not ones this skill is about to create.
Later, `check_evidence.py verify` allows only `??` (untracked) paths, and
only inside the output directory; a tracked modification anywhere, or an
untracked file outside the output directory, fails the check. One
subtlety worth knowing before it surprises you: if `--repo-root` points at a
subdirectory of a larger git repository, `git status` still reports the
whole repository's status, not just that subdirectory, so an unrelated
untracked file elsewhere in a monorepo is reported as an integrity problem
too. That is the safe direction to err in -- the study may well have caused
it -- but it can be noisy outside the directory actually under study; check
whether the flagged path is related before assuming the pipeline broke
something.

What the git check cannot see: `git status` does not report paths excluded by
`.gitignore`, and `check_evidence.py` does not ask it to. A write into an
ignored path inside the repository under study -- a `__pycache__/` directory
beside an imported module, a build or coverage directory, a tool's cache --
passes the git integrity check in silence. Do not patch around that with an
ad-hoc scan of ignored files: Phase 1 records no baseline of which ignored
paths already existed, so such a scan cannot tell a file this run created
from one that was there all along, and it would produce noise rather than
evidence. Two things follow. First, the honest mitigation is upstream --
`<skill-dir>/experiments.md` requires every experiment to run with its
language's cache and artifact writes suppressed, so those writes never happen
in the first place. Second, state the boundary of the guarantee accurately
when reporting: the git pass proves that nothing git tracks changed and that
nothing untracked-and-unignored appeared outside the output directory, which
is not the same claim as the repository being byte-for-byte identical.
(Snapshot mode has the opposite shape: its walk consults no ignore file and
so does cover ignored paths, which is also why it cannot be pointed at a git
work tree -- ordinary `.git` churn would fail it.)

For a repository with no version control at all: run
`check_evidence.py snapshot` before producing any outputs. Snapshot mode is
reserved for genuinely non-git repositories -- it is not a stronger
alternative to run inside a git repository "just in case." The snapshot walk
does not exclude `.git`, so running it inside an actual git work tree
produces spurious failures from ordinary index churn (`.git` mtimes change
on nearly every git operation). If the repository is a git work tree, use
the git integrity path above, full stop. The snapshot itself records file
size and mtime for every file outside the output directory, plus a sha256
hash for every cited file; because mtime is part of the baseline, a
content-identical rewrite (a formatter touching a file without changing its
bytes, a build step that re-links but does not re-generate) still fails
`verify` with `"<path>: mtime changed"`. That failure is intentional
paranoia for a read-only study, not a bug to work around -- the fix is to
re-run `snapshot` and re-baseline, never to loosen the check or ignore the
finding.

When Phase 2 needs to cite a file that Phase 1's snapshot never hashed, run
`check_evidence.py extend-snapshot`, not a fresh `snapshot`. `extend-snapshot`
first re-verifies the existing baseline and only then adds hashes for the
newly cited files; if something has already changed underneath the baseline,
it refuses to extend, because extending an already-broken baseline would
launder an earlier, unexplained change into the new one instead of surfacing
it.

## Phase 1 exit criteria

Do not move to Phase 2 until all of the following exist:

- a resolved study boundary, with excluded components named for the
  Boundary note;
- contract evidence: signature, docstring, and test behavior, cited;
- a caller map covering every in-repo caller and the nearest public API path;
- initial invariants and state notes;
- a comprehension ledger (`<stem>_study.notes.md`) in the exact grammar
  above, with at least the contract, caller, and invariant claims entered;
- an integrity baseline -- a clean git status, or a written
  `check_evidence.py snapshot`.

A Phase 1 that skips any of these is not a shorter study; it is an
unverifiable one, and Phase 5 will catch it late instead of Phase 1 catching
it early.
