# Experiments

Experiments are how Phase 2 answers a trade-off that reasoning alone cannot
settle. They are the only place in this pipeline that runs code, and running
code the skill did not write, against a repository it does not own, is a
privileged act -- everything below exists to keep that act honest, approved,
and reproducible.

This executes code from the repository under study and adds no sandbox
beyond not writing to it. There is no container, no restricted interpreter,
no network isolation layered on top -- the only guarantee this pipeline adds
is that nothing it runs writes outside the experiment directory. Treat every
proposed experiment with the same care you would give to running someone
else's script directly, because that is exactly what it is.

`<experiments-dir>` below is `<stem>_study_experiments/`, the experiments
output path `SKILL.md` resolves once, in Phase 1, alongside the study's
other four output paths -- not a location this doc invents on its own.

## Plan format

Every experiment is proposed in `<experiments-dir>/PLAN.md` as one line,
starting unchecked:

```
- [ ] [C12] bench_deque.py -- Ground the queue-operation trade-off; run the project wrapper against copied fixtures; under 30 seconds; CPU only; create a scratch venv under this directory.
```

The line names the ledger ID the experiment supports, the script that will
run, and, after `--`, what it measures, how, and its bounds. Propose it and
stop. Do not create the script, run anything, or write any output until the
user has approved that exact entry.

## User response and approval states

The user's response to a batch of proposed experiments is one of four
things: approve all, approve a subset, revise (change the script, the bound,
or the ledger ID before approving), or skip entirely. Handle each precisely:

- **Approve all** -- every proposed line moves from `[ ]` to `[x]`.
- **Approve a subset** -- only the approved lines move to `[x]`; the rest
  stay `[ ]` (still proposed, not yet decided) or move to `[~]` if the user
  explicitly declined them rather than merely deferring.
- **Revise** -- do not check the old line. Replace it with a new `[ ]` entry
  reflecting the revision, and mark the original `[-]` (superseded) so the
  history of what was proposed and changed stays in the file rather than
  being overwritten.
- **Skip** -- the line becomes `[~]` (declined). Record the decline in the
  ledger too: the corresponding claim is derived from what is already known,
  or omitted, per `investigation.md`.

After approval, change only the checkbox -- `[ ]` to `[x]` -- never the rest
of the line. If the script or bounds need to change after approval, that is
a revision: supersede the old line and propose a new one, do not silently
edit an approved line in place. `check_evidence.py` recognizes only `[x]` as
an approved entry (see `PLAN_RE` in `check_evidence.py`); `[~]` and `[-]`
exist so the plan file stays an honest, auditable record of every proposal
and its outcome, not so the checker treats them as approvals.

## Reproducibility requirements

Every experiment directory must contain, alongside the script:

- copied inputs and copied alternative implementations under the experiment
  directory -- never a path reaching back out to a scratch location the
  study does not own;
- the reproducible script itself. Run through the project's command
  wrapper, never a bare interpreter. Use the same wrapper the project's own
  tests or benchmarks use (`make bench`, `tox`, a documented
  `scripts/run.sh`, whatever this specific repository actually uses); a
  bare `python foo.py` may silently pick up the wrong interpreter, the
  wrong virtualenv, or the wrong flags, and the measurement would then say
  something true about the wrong thing;
- the captured `.out` file for every run, referenced by the ledger's
  `measure: <script> -> <output>` entry;
- one `ENV.md` per experiment directory, covering every run in it, recording:
  machine, OS, accelerator (or "CPU only"), runtime and library versions,
  the repository's commit SHA when the repository has one, the date, the
  exact wrapper command used, and the installed package versions relevant to
  the measurement.

If a measurement needs an isolated dependency set, the plan may call for a
scratch venv (or equivalent) created under the experiment directory itself,
as in the example above -- still inside the directory this pipeline owns,
never touching the ambient environment or a location outside the study's
output.

## Suppress generated cache and artifact writes

Running the repository's own code makes the language write into the
repository unless it is told not to. Python drops a `__pycache__/` directory
beside every module it imports; other toolchains have their own equivalents
-- a test runner's cache directory, a coverage data file, a compiler's object
or build directory, a package manager's local cache. Those writes land inside
the repository this study promised not to touch, and they land on exactly the
paths a `.gitignore` already covers, which means Phase 5's git integrity
check does not see them and reports clean anyway. The suppression below is
what actually keeps the promise; the checker cannot.

Suppress the writes in the experiment's own command and environment, before
the first run -- never by deleting artifacts afterward, which is another
write into a repository the study does not own:

- Python: set `PYTHONDONTWRITEBYTECODE=1` in the wrapper invocation, and
  redirect any cache a tool insists on writing to a path under
  `<experiments-dir>` (for example `PYTEST_ADDOPTS=-p no:cacheprovider`, or
  an explicit `--cache-dir` under the experiment directory).
- Every other language and build system: find its equivalent before the
  first run -- the flag that disables writing compiled output, or the
  environment variable that moves a cache or build directory -- and point it
  at a path under `<experiments-dir>`.

This is part of the wrapper command and environment, not a separate cleanup
step, and it is recorded verbatim in `ENV.md` alongside the rest of the
invocation so a later reader can see the measurement ran with the suppression
in place. An experiment that cannot be made to run without writing into the
repository under study is a declined experiment, not an exception to the
safety invariant: record the decline in `PLAN.md` and in the ledger, then
derive the claim from what is already known or omit it.

## Semantic equivalence before timing

Before timing anything, establish that the implementations being compared
actually compute the same thing on the same inputs -- same output, same
edge-case behavior, on at least one shared input. A benchmark that times two
functions that quietly disagree on an edge case measures nothing useful.
Only once equivalence is established does timing methodology matter:

- warm up before recording, so the measurement is not dominated by
  first-call cost (JIT warmup, cache population, lazy imports) unless that
  cost is itself the thing under study;
- run enough repetitions to report a spread (min/max or a simple
  distribution), not a single number that could be noise;
- state the repetition count and the bound on total runtime up front, in
  the plan line, so the user is approving a bounded cost;
- use like-for-like inputs across every implementation compared -- same
  size, same shape, same distribution.

## A failed experiment is a result

An experiment that errors, times out, or produces a result contradicting the
expected trade-off is not a failure to hide or quietly re-run until it looks
right. A failed experiment is a result. Capture the `.out` file (or the
error output) exactly as produced, record what happened in the ledger as a
`measure:` entry pointing at that captured output, and let Phase 3 write
honestly about what was found, including "the two implementations perform
within noise of each other" or "the experiment could not be made to run
under the project's wrapper." Re-running silently until a preferred number
appears is exactly the failure mode the evidence discipline exists to
prevent.
