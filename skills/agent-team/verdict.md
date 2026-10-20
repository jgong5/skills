# verdict: the owner rules on held items

`/agent-team verdict [text]` answers `Needs owner ruling:` requests. It
posts the owner's ruling where the request is, makes the GitHub changes the
ruling calls for, removes `need human`, and tells the runs waiting on it.

## 0. Load

Step 0 (`SKILL.md`), except that an overlay problem stops `verdict`: a
ruling posted under a wrong `repo` reaches the wrong items, and no draft is
worth that.

## 1. Scope

- `#N` numbers, labels or "all" in the text name the items; "all" is every
  open `need human` issue and PR in `<repo>`.
- Otherwise it is the held item last discussed in this conversation; an
  `advise` (`advise.md`) discusses the item it analysed.
- Ask when that is ambiguous: none discussed, or several.

An **item** is an issue plus every open PR that delivers it (`rules.md`,
Check delivery) or is labeled for its ruling (`rules.md`, Escalations). A
PR named alone brings its issue. Read every member's thread: the request,
its options and its recommendation.

## 2. Decide

The decision comes from, in rank order: the owner's words in this
conversation, the text, an `advise` recommendation in this conversation,
and the request's recommendation. One item is acted on as
decided. Several are shown first as one table -- item, decision, the
actions step 3 will take, there and outside it -- and confirmed once.

## 3. Act, per item

1. **Post the Ruling** where the request is, in `gh-prose`'s Ruling shape,
   linted as `--kind comment`:

   ```
   Ruling: (a) keep the cut. Splitting moves the same lines into two reviews.
   Also: #41 commented, #45 opened, #43 brief updated.
   ```

   The first line opens with plain `Ruling:`, never bold: `pr_state.py`
   restarts its `verdicts` count only at that form. Each other open member
   PR gets `Ruling: <link to it>.`, so its thread carries the ruling and its
   count restarts too. The Ruling's `Also:` line comes from item 3.
2. **Edit the issue body** when the ruling changes the brief, and add
   `Brief updated: <parts>.` to the Ruling. A split is `plan`'s: run it now
   with `#N` as input, and leave the label on until it publishes the
   sub-tasks.
3. **Close, reopen or open issues** the ruling calls for, yourself: a
   close carries its handoff comment, an opened issue a brief (`plan.md`,
   step 3) that links the Ruling. Each issue or PR outside the item that
   the ruling affects gets a comment linking it, linted as `--kind comment`:

   ```
   Ruling on #38 affects this: it now waits for #45.
   <link to the Ruling>
   Brief updated: Depends on.
   ```

   When the ruling changes its brief or `Depends on` lines, edit its body
   and add `Brief updated: <parts>.` to the comment. A held one gets the
   comment only and keeps its label: its own request still needs a ruling.
   An affected issue's open delivering PRs (`rules.md`, Check delivery)
   get the comment too: `pr_state.py` reads only a PR's own thread, so
   without it an approved PR lands against the old brief.
   Then edit the Ruling so `Also:` is its last line.
4. **Leave git work to the developer.** No commit, push or merge here; the
   next pass acts on the Ruling through whichever role `pr_state.py` gives
   the turn.
5. **Unlabel every member** last, so no run sees an item unheld before
   its ruling is on GitHub.
6. **Tell the runs.** `SendMessage` each peer session in `ListAgents` that
   works in this project: `Ruling posted on #N in <repo>; also affects #X,
   #Y, and opened #Z. Run one pass if your scope covers any of them.`,
   dropping empty parts. `ListAgents` shows no working directory; the
   session records, `~/.claude/sessions/<pid>.json`, hold each session's
   `name` and `cwd`, and are undocumented Claude Code internals. Find this
   session's record by the name `ListAgents` gives it; a peer is in the
   project when its record's `cwd` is that `cwd` or a directory under it.
   Compare record paths only with each other, never with a path a container
   wrapper reports: the two can differ. When the records cannot be read or
   this session's is missing, message every peer `ListAgents` lists and say
   so in the report: a missed run waits an hour for its check, an extra
   message is ignored. When this session has a `run` check pending
   (`CronList`), run one pass here as well.

**Done when** every item in scope carries its Ruling, has no `need human`
left (a split's after `plan` publishes), every item it affects has its
comment and every peer was messaged; report each Ruling's link and what
changed, there and outside it.
