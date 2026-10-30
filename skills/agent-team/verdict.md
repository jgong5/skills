# verdict: an item's ruler rules on it

`/agent-team verdict [text]` answers ruling requests on the items the
current `gh` user rules (`rules.md`, Escalations). It posts the ruling where
the request is, makes the GitHub changes the ruling calls for, and removes
`need human`; or it hands an item to another ruler. A run in scope sees the
Ruling at its next check (`SKILL.md`, The check).

## 0. Load

Step 0 (`SKILL.md`), except that an overlay problem stops `verdict`: a
ruling posted under a wrong `repo` reaches the wrong items, and no draft is
worth that.

## 1. Scope

- `#N` numbers, labels or "all" in the text name the items; "all" is every
  open `need human` item in `<repo>` whose ruler is the current user
  (`gh api user`). List the others, each with its ruler, and act on none.
- Otherwise it is the held item last discussed in this conversation; an
  `advise` (`advise.md`) discusses the item it analysed.
- Ask when that is ambiguous: none discussed, or several.

An **item** is an issue plus every open PR that delivers it (`rules.md`,
Check delivery) or is labeled for its ruling (`rules.md`, Escalations). A
PR named alone brings its issue. Read every member's thread: the request,
its options and its recommendation.

## 2. Check the ruler

Run `python3 <skill-dir>/ruler.py N --repo <repo>` for each item. When the
current user is not its ruler, refuse both the Ruling and the hand-off for
that item, and name the ruler as the one who rules on it or hands it on, or
say it has none: the way on is the ruler's, not this session's, so suggest
no request line or reassignment that would make it yours. An item with no
ruler gets no Ruling: with several assignees any of them may hand it off,
and with none this session assigns nothing; the item gets a ruler when
someone assigns it or a request names one.

**Hand-off.** When the text hands the item on ("hand to @x"), post
`Needs ruling from @x: <link to the request>.` where the request is, linted
as `--kind comment`, and stop there: the label stays.

## 3. Decide

The decision comes from, in rank order: the owner's words in this
conversation, the text, an `advise` recommendation in this conversation,
and the request's recommendation. One item is acted on as
decided. Several are shown first as one table -- item, decision, the
actions step 4 will take, there and outside it -- and confirmed once.

A `Ruling on #M affects this:` comment posted after the request is part of
the question: the Ruling answers it (`Also applies the Ruling on #M: ...`),
or says why not.

## 4. Act, per item

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
   and add `Brief updated: <parts>.` to the comment. That holds for an
   unheld one with no assignee or assigned to you. Otherwise:
   - a held one, whoever rules it, gets the comment only, mentioning its
     ruler, and keeps its label: its own request still needs a ruling;
   - an unheld one assigned only to others is not edited: its comment
     opens `Needs ruling from @<assignee>:` instead, and it and its open
     PRs get `need human`.

   An affected issue's open delivering PRs (`rules.md`, Check delivery)
   get the comment too: `pr_state.py` reads only a PR's own thread, so
   without it an approved PR lands against the old brief.
   Then edit the Ruling so `Also:` is its last line.
4. **Leave git work to the developer.** No commit, push or merge here; the
   next pass acts on the Ruling through whichever role `pr_state.py` gives
   the turn.
5. **Unlabel every member** last, so no run sees an item unheld before
   its ruling is on GitHub.

**Done when** every item in scope that the current user rules carries its
Ruling and has no `need human` left (a split's after `plan` publishes), or
carries its hand-off, and every item it affects has its comment; report
each Ruling's link and what changed, there and outside it, and each refused
item with its ruler.
