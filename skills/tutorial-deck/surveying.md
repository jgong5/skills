# Phase 1: Survey

Phase 1 pins one version of the repository and writes down what is true about
the topic before anything is decided about the deck. It produces `survey.md`.
Nothing here is a teaching choice: "the scheduler retries a failed request
once" is Phase 1 work; "open the talk with that retry" is the interview's.

Every later phase grounds itself in this file. The interview's recommended
answers cite it, the outline's slides trace to it, and the fact-check reviewer
checks the deck against it. A fact missing here is a fact the deck cannot use
without going back to the code, so the survey is where the reading happens,
once.

## Pin the commit

Before reading anything, fix the version every citation will refer to.

In a git work tree, record `git rev-parse HEAD` and the branch name. That
commit is printed in every slide footer, and every `path: symbol` citation in
the deck means "at this commit". A citation without a pin goes stale the next
time someone pushes; a citation with one stays checkable for as long as the
commit exists.

Then run `git status --porcelain`. If any file that belongs to the topic has
uncommitted changes, **stop and ask** the owner whether to commit, stash, or
study the committed version. Do not choose for them: an uncommitted change
is either the work the talk is about or noise the talk must not teach, and
only the owner knows which. Uncommitted changes outside the topic are
recorded in `survey.md` and do not stop the run.

Outside a git work tree, record the absolute path and today's date as the
pin, and say in `survey.md` that there is no version baseline. The deck's
footer then carries the path and date, and the final report says that the
citations cannot be re-checked against a later state of the code.

The repository is read-only for the whole run. Reading never writes, and
nothing this skill produces lands outside the output directory.

## Read the topic, and only the topic

**The reading boundary is the set of files that implement, configure, or
explain the topic.** Not the repository, not the subsystem the topic lives
in. A tutorial about one mechanism that surveys the whole codebase spends its
reading on facts no slide will use, and the extra material leaks into the
deck as detours.

Work outward from where the topic enters the code: the public function, the
command, the config key, the request handler the topic's name points to.
Follow calls while they stay on the topic. Stop at a call whose behaviour the
deck can state from its name and signature alone, and record it as an edge
with that one-line statement.

Read these kinds of source, in this order:

- **Code.** What the mechanism does, at the pinned commit. This is the only
  source for how the code behaves; a design doc that disagrees with the code
  is recorded as a disagreement, and the code wins for every claim about
  behaviour.
- **Design docs.** Design notes, RFCs, ADRs, the comments above the topic's
  core functions, and the README sections that describe it. These are the
  source for why the code is shaped this way and what was rejected.
- **Issues and pull requests.** Search them for the topic's symbols and
  terms. They are the source for real incidents -- what broke, how it was
  seen, and which change fixed it -- and often for the alternative a design
  decision rejected. Read them through the repository's own tooling (`gh`
  when the host is GitHub); when they are unreachable, say so in `survey.md`
  and leave the incidents section empty rather than inventing typical ones.

A source outside the repository (a paper, a vendor manual) is read only when
the code or a design doc names it, and is cited by title and section.

## Write `survey.md`

Write `survey.md` in the output directory as soon as the interview's first
question fixes that directory. Until then the survey is held as a draft and
nothing is written anywhere, because the repository is read-only and no other
location belongs to this run.

`survey.md` opens with the pin (commit and branch, or path and date) and the
reading boundary with its recorded edges. Then one section per kind of
finding below. Every entry carries its source: `path: symbol` for code, a
document path and heading for a design doc, an issue or PR number for an
incident. An entry with no source is either found one or dropped -- the
deck's discipline is cite, derive, or omit, and that starts here.

- **Concepts.** The ideas a newcomer needs before the code makes sense: the
  terms, the invariants, the theory the topic rests on. For each, where the
  code embodies it. These become the vocabulary the deck defines on first
  use.
- **Mechanisms.** What the code does to solve each problem the topic exists
  for: the data structures, the control flow, the hand-offs between
  components. For each, the failure it prevents -- what would go wrong
  without it. A mechanism with no stated failure cannot be taught failure
  first, so finding the failure is part of surveying the mechanism, not
  something to improvise on the slide.
- **Design decisions.** Each choice the code embodies that a reasonable
  engineer might have made differently, with the alternatives it rejected
  and the reason, cited to the design record that states it. A decision
  whose rejected alternative is not written down anywhere is recorded with
  "alternative not recorded", not with a guessed one. Numbers that go with a
  decision -- a measured cost, a benchmark, a size limit -- are copied from
  the record with their source.
- **Real incidents.** Bugs, outages, and regressions the topic caused or
  fixed, each with its issue or PR, the symptom as reported, the cause, and
  the change that fixed it. These are the deck's best failure-first
  material, because the audience will meet the same symptoms.
- **Runnable cores.** The smallest pieces of the topic that can be run
  standalone: a pure function, a test that isolates the mechanism, a script
  the repository already ships. For each, how it is invoked through the
  project's own wrapper and what input it needs. The outline's replay script
  for the hardest concept starts from one of these. A topic with none is
  recorded as having none; the step-through is then hand-derived and marked
  so in the slide notes.

Close `survey.md` with an **open questions** list: facts the reading could
not settle. They stay off slides unless a later lookup settles them, and the
deck's notes carry the ones a slide depends on.
