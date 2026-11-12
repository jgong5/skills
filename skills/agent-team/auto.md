# auto: from a requirement to an umbrella

`/agent-team auto <prompt | #N | path>` takes what the owner wants built
and asks the owner once, at the requirement confirmation. Before it,
`auto` reads, runs and drafts; after it, `auto` sets up the integration
branch, opens the umbrella issue and its design issue, and hands over to
`run` scoped to the umbrella. From there agents decide how to build; the
owner is asked again only about what to build, about an action outside the
repository, and at acceptance.

**Nothing before the confirmation leaves scratch** (`<scratch>`: the
project's git-ignored scratch directory, or one the overlay body names) or
the baseline's temporary directory: no issue, comment, label, branch, push
or repository, and no change to a tracked file.
The owner can still say no, so stopping at the confirmation must leave no
trace.

## 1. Read

Step 0 (`SKILL.md`), except that an overlay problem does not stop `auto`
(it is one of the cases in step 3) and labels wait for step 6. A path is
read; `#N` is read with its comments, after checking delivery
(`rules.md`); anything else is the requirement itself. Read
`<design_entry>` when the overlay loads, else the repository's `CLAUDE.md`
or `AGENTS.md`, and the code the requirement touches.

## 2. The requirement

Read `<skill-dir>/../auto-grilling/SKILL.md` only up to its `# Part 2`
heading (`sed '/^# Part 2/q'`) and run that loop on the requirement,
writing its log in `<publish_language>`, since its Summary becomes
published text. The loop's ending is this doc's confirmation (step 5),
never `auto-grilling`'s menu, which is why Part 2 stays unread.

- **Ask requirement-level questions only**: what to build and for whom,
  the goals and their priority, how success is measured, what is out. A
  question about how to build -- a module, an algorithm, an interface's
  shape -- belongs to the designer and is skipped, not answered: an answer
  here would bind the design before anyone has read the code for it.
- **Leave the Summary's `Changes` line out**, and drop "the change per
  module or file" from the loop's Done when: that is how to build.
- **Every acceptance item is measurable and names its command**, run from
  the repository root, with the output that counts as met. An acceptance
  command is not `gate_task`: it may be expensive (a GPU accuracy run), so
  only the acceptor runs it.
- A `low` answer becomes a question in the confirmation.

Write the Summary out as `<scratch>/<topic>.requirement.md`, `<topic>`
being the loop's name for its `<topic>.grill.md`:

```
# Requirement: <feature>
Source: <the prompt, quoted | #N | path>

## Goals
1. <goal>             (highest priority first)

## Acceptance
- A1. <measurable claim>. Check: `<command>`; met when <output>.

## Scope
## Non-goals
```

**Done when** every goal has an acceptance item and every acceptance item
has a command.

## 3. The environment

The integration branch defaults to the current checkout's, and the
repository to the current checkout's `repo` (or `git remote -v`); the
requirement may name others. The first case that matches applies:

1. **New project** -- the repository does not exist on GitHub (`gh repo
   view <repo>` finds none). Draft its name and visibility. With no
   checkout, also draft its local clone path (default: beside the current
   repository) and an overlay whose `gate_task` is trivially green and
   whose `design_entry` is case 5's empty index; with a checkout, continue
   as case 5 on it.
2. **Fork** -- the requirement says so, or the current `gh` user cannot
   push to the repository (`gh repo view <repo> --json viewerPermission`
   below `WRITE`). Draft the upstream, the fork's owner and the base ref,
   then continue as case 5 on the upstream's checkout, with `repo` the
   fork and `never_touch` the upstream.
3. **Overlay present** -- `python3 <skill-dir>/overlay.py --ref
   <remote>/<branch>` exits 0. Use it; nothing about it is asked.
4. **New line** -- the branch does not exist on `<remote>`, and the branch
   it starts from has an overlay that loads. The draft is that overlay
   with `integration_branch` set to the new branch; other values carry
   over unless the owner changes them.
5. **No overlay** -- draft it as `overlay.md` (Drafting) steps 1-4 say,
   every value with the source it came from. With no `CLAUDE.md`,
   `AGENTS.md` or README to name, `design_entry` is `docs/README.md`,
   drafted as an empty index and committed with the overlay, so the design
   document and the principles have a directory.

In cases 1 and 2 step 6 creates `repo`, so no remote points at it yet:
their overlay draft sets `remote` to `origin`, the name step 6 gives it.

**The baseline.** Whenever there is a checkout, run the gate once
(`overlay.md` step 3) in a `git archive` snapshot of the branch tip --
`<remote>/<branch>` as fetched, a new line's start point, or `HEAD` when
the repository is new -- extracted into `mktemp -d`, outside the
repository, so no test runner climbs from the snapshot into the
checkout's own configuration. Record the command, how it ran (wrapper,
container, interpreter), the sha, the exit status and the wall time. A
red baseline does not stop `auto`: it takes `overlay.md` step 4's second
way on and drafts a project-owned wrapper script that runs the gate,
excludes each known failure by name and fails on anything else. The
wrapper becomes `gate_task`; rerun it in the snapshot to show it green.
A failure with no stable name, or one so broad the wrapper would exclude
most of the suite, is not wrapped: it is a question.

Draft a brief (`plan.md`, step 3) for each excluded failure, since
nothing later in auto mode writes one and `run` never claims an issue
without it: its file set the test, the code it fails in and the wrapper;
its exit criteria and named result the test passing with the wrapper no
longer excluding it; its effort as `plan.md` step 3 states it, estimated
from reading the failure. A failure whose cause the reading does not
find is a question, not a brief.

**The local file.** When `.claude/agent-team.local.md` is missing, draft
one whose body says how the baseline actually ran: the wrapper or
container command, the interpreter, any path mapping. Read
`CLAUDE.local.md` and each parent directory's `CLAUDE.md` for them, since
a shared machine records its conventions above the repository.

**Load the drafts** when an overlay or a local file was drafted: `run`
stops at Step 0 on any problem `overlay.py` reports, a local file with no
`---` block included. Put the overlay as it will be committed (the draft
or the present one) in `<scratch>/<topic>.overlay/agent-team.md` and,
beside it as `agent-team.local.md`, the local file draft or else the
present `.claude/agent-team.local.md`, which `run` reads too. The command
line reads only the work tree's overlay or a committed one, so from the
checkout (the current one when a new project has none yet) load them by
path, and rerun whenever a draft changes:

```
python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import overlay; p = overlay.load(sys.argv[2])[2]; print(*p, sep="\n"); sys.exit(bool(p))' <skill-dir> <scratch>/<topic>.overlay/agent-team.md
```

**Done when** the case is chosen, every overlay value has a source, the
baseline has a result and each excluded failure a brief, the drafts load,
or what stopped it is a question.

## 4. Principles

The principles in force are `<skill-dir>/principles.md` with the
project's layer on top, as that file says. Only the project's layer is
yours: when the project has a principles document (in `<design_entry>`'s
directory, indexed by `<design_entry>`), it is that layer as it stands;
otherwise draft one in `<publish_language>`, in the shape of
`<skill-dir>/principles.md`: each principle one or two sentences, its why,
and a link to its source. Either way, list each default the layer
overrides: a project principle that conflicts with one of the default list.

- A new project has no Rulings: skip the search below, and add the
  requirement's non-goals and priorities to the sources it has.
- Sources: the design documents `<design_entry>` indexes, `CLAUDE.md`,
  the overlay body, and past human Rulings. Find those with `gh search
  issues "Ruling:" --repo <repo> --include-prs --limit 1000` (without
  it, a long ruling history yields a silent sample) and read the comments
  whose first line opens with plain `Ruling:`; a `Ruling (auto):` is an
  agent's and is never a source.
- Cluster the Rulings by the reason they give. A reason that recurs is a
  principle, linking two or three of its Rulings; one Ruling alone is a
  precedent, not a principle.
- Keep only what is specific to the project: a principle
  `<skill-dir>/principles.md` already states is not restated.

The draft lands with the design PR, so the design issue carries it.

## 5. The confirmation

One message to the owner, in the owner's language (`rules.md`, Talking to
the owner), quoting each draft rather than pointing at scratch:

1. **The requirement document.**
2. **The environment**: the case, the integration branch, and, as the
   case needs, the new repository's name, visibility and clone path, or
   the fork's upstream, owner and base ref; then each action step 6 will
   take, in order.
3. **What was verified**, each with its source, for approval with the
   rest and no question asked: the overlay draft value by value, the
   baseline result, the wrapper, the failures it excludes and their
   briefs, the local file draft, the drafts' load command and its exit
   status, and the principles in force: the default list, linked, then
   the project's layer, quoted and marked existing or drafted, then each
   default it overrides.
4. **What is asked**: everything not found or not verified -- no gate
   candidate, no working environment, several ways to run that differ, an
   action outside the repository, a red baseline too broad to wrap --
   and each `low` answer from the loop with its recommendation.

Wait for the owner. An answer that changes something is applied, what
depends on it is redone (the log's `Depends on` lines; a changed gate
reruns the baseline), and the changed parts are shown again. Approval
covers the values as last shown.

**Done when** the owner has approved and every question has an answer.

## 6. Publish and hand over

In this order, linting every GitHub text with `gh-prose` first:

1. **Set up the environment** for the case. A commit below that carries
   the overlay also carries the local file's `.gitignore` line
   (`overlay.md`) when a local file was drafted:
   - new project: `gh repo create`. With a checkout, add it as `origin`
     (`--source . --remote origin`), push its branch as it is, then as no
     overlay. Without one, clone to the approved path and
     push an initial commit with a minimal skeleton, the overlay and its
     trivially green gate; the design states the test strategy, and the
     first scaffold task replaces `gate_task` through its PR;
   - fork: `gh repo fork --remote` in the upstream's checkout, which names
     the fork `origin` and the upstream `upstream`, `gh repo set-default
     <fork>` there, then as no overlay;
   - new line: create the branch at its start point and push one
     bootstrap commit straight to it, the overlay (and any wrapper) as
     approved: until the line's overlay names it, a run there would load
     the parent's `integration_branch` and land on the parent;
   - no overlay, or a red baseline under a present overlay: commit the
     overlay and any wrapper on a branch and open a PR into the
     integration branch. Until it lands, every script reads the overlay
     with `--ref <remote>/<PR branch>` (`overlay.md`).
2. **Write the local file** when one was drafted, beside the checkout's
   overlay, and its ignore line in `.git/info/exclude`: a committed
   `.gitignore` line serves other clones, but reaches the main worktree
   only once its commit lands, and until then the file shows as untracked.
3. **Create the labels** `agent-team/auto` and `agent-team/design` when
   missing.
4. **Open the umbrella**: titled with the feature, labeled
   `agent-team/auto`, its body `Integration branch: <branch>`, then,
   while the overlay is in a PR, `Overlay: <remote>/<PR branch> (#P)`,
   then the requirement document in `<details>`, which keeps the
   `gh-prose` word budget without cutting an acceptance item. The
   umbrella is never a task.
5. **Open the design issue**: `Design: <feature>`, labeled
   `agent-team/design`, its body opening `Part of #U` and holding a brief
   (`plan.md`, step 3) whose file set is the design document in
   `<design_entry>`'s directory, `<design_entry>` itself when it lists
   the design documents, and, when one was drafted, the principles
   document. The body quotes the approved principles draft in full, in
   `<details>`: the designer commits it with the design, as approved.
6. **File one issue per excluded failure**, each `Part of #U`, with the
   test's failing output and its approved brief, plus `Depends on #P` when
   the wrapper is in the overlay PR, since the fix edits it.
7. **Enter `run`** with scope `#U`, adding the overlay PR when there is
   one so it is reviewed and landed like any other. No approval gate
   follows: the confirmation was it.

**Done when** the umbrella and its design issue exist and `run` has
started on the umbrella.
