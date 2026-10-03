# The project overlay

`<repo>/.claude/agent-team.md` carries everything project-specific. Its
frontmatter is flat `key: value` lines (`#` starts a comment line); its body
is free text -- project rules and environment notes every role reads, such
as container ownership fixes or what to run after a container rebuild.
`overlay.py` parses it, fills defaults, resolves `remote`, and lists every
problem; it rejects unknown keys so a typo cannot silently fall back to a
default.

| Key | Required | Default | Meaning |
|---|---|---|---|
| `repo` | yes | -- | `OWNER/NAME` agents write to. No default: `origin` is often an upstream agents must not touch. |
| `integration_branch` | yes | -- | Where PRs land, squashed. |
| `gate_task` | yes | -- | The per-task gate. Runs from a worktree's root; exit 0 is a pass. Join commands with `&&`. |
| `design_entry` | yes | -- | The document developers and reviewers read first (design principles, or the README that indexes them). |
| `remote` | no | the one remote whose URL points at `repo` | Name of that remote; set it only when zero or several match. |
| `never_touch` | no | -- | Repositories agents never write to (comma-separated), typically the upstream. |
| `gate_wave` | no | -- | A wider, slower gate run on `integration_branch` after a run lands work; never blocks a landing. |
| `new_tests_dir` | no | -- | Where a task's new tests go. |
| `import_check` | no | -- | Command printing where the project's package resolves from, run in each tree. |
| `worktree_root` | no | `<main worktree>-worktrees`, beside it | Parent of the per-task worktrees. |
| `publish_language` | no | `English` | Language of everything published to GitHub. |
| `max_tasks` | no | `5` | Tasks in flight; agents in flight are at most twice this. |
| `split_loc` | no | `1000` | A task estimated above this many lines, tests included, is decomposed. |
| `task_label` | no | -- | When set, only open issues with this label are in the pool; when absent, every open issue in `repo` is. |

## Drafting a missing or broken overlay

`plan` and `run` stop here until the overlay loads clean. Draft it with the
owner; every value you propose carries the source you read it from.

1. **Infer.** `repo` and `remote` from `git remote -v` (offer the candidates;
   flag any remote that looks like an upstream as a `never_touch`
   candidate). `integration_branch` from the default branch and any branch
   the project's docs name. `design_entry` and `new_tests_dir` from the
   repository's layout and its `CLAUDE.md` / `AGENTS.md`.
2. **Find `gate_task` candidates**, in this order, and stop at the first that
   names a command: the test and lint commands in `CLAUDE.md` / `AGENTS.md`;
   the `run:` steps of `.github/workflows/*.yml` that run on pull requests;
   the conventional entry points of the build manifest (`pyproject.toml`
   pytest settings, `package.json` scripts, a `Makefile` `test` target,
   `Cargo.toml`). Combine test and lint into one `&&` line.
3. **Run the candidate once** on the tip of `<integration_branch>`, in a
   worktree or `git archive` snapshot, and report its exit status and wall
   time. This run is the baseline every later gate is judged against.
4. **A red baseline stops the drafting.** Offer the owner these ways on: a first
   task that makes the baseline green, or a project-owned wrapper script that
   excludes the known failures by name (and fails on anything else), which
   then becomes `gate_task`. This skill keeps no list of known failures,
   because what counts as known differs per project and a list kept here
   would go stale unseen.
5. **Write the file only after the owner approves the values**, then rerun
   `overlay.py` until it exits 0.
