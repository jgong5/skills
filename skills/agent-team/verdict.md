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
- Otherwise it is the held item last discussed in this conversation.
- Ask when that is ambiguous: none discussed, or several.

An **item** is an issue plus every open PR that delivers it (`rules.md`,
Check delivery) or is labeled for its ruling (`rules.md`, Escalations). A
PR named alone brings its issue. Read every member's thread: the request,
its options and its recommendation.

## 2. Decide

The decision comes from this conversation and the text; take the request's
recommendation only when neither settles it. One item is acted on as
decided. Several are shown first as one table -- item, decision, the
actions step 3 will take -- and confirmed once.

## 3. Act, per item

1. **Post the Ruling** where the request is, in `gh-prose`'s Ruling shape,
   linted as `--kind comment`:

   ```
   Ruling: (a) keep the cut. Splitting moves the same lines into two reviews.
   ```

   The first line opens with plain `Ruling:`, never bold: `pr_state.py`
   restarts its `verdicts` count only at that form. Each other open member
   PR gets `Ruling: <link to it>.`, so its thread carries the ruling and its
   count restarts too.
2. **Edit the issue body** when the ruling changes the brief, and end the
   Ruling with `Brief updated: <parts>.` A split is `plan`'s: run it now
   with `#N` as input, and leave the label on until it publishes the
   sub-tasks.
3. **Close, reopen or open issues** the ruling calls for, yourself: a
   close carries its handoff comment, an opened issue a brief (`plan.md`,
   step 3).
4. **Leave git work to the developer.** No commit, push or merge here; the
   PR's developer acts on the Ruling at the next pass.
5. **Unlabel every member** last, so no run sees an item unheld before
   its ruling is on GitHub.
6. **Tell the runs.** `SendMessage` each peer session in `ListAgents` whose
   name starts with `<repo>`'s name (the part after `/`): `Ruling posted on
   #N in <repo>. Run one pass if your scope covers it.` When this session
   has a `run` check pending (`CronList`), run one pass here as well.

**Done when** every item in scope carries its Ruling, has no `need human`
left (a split's after `plan` publishes), and every peer was messaged; report
each Ruling's link and what changed.
