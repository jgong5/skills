# advise: why a held item is stuck, and what to rule

`/agent-team advise <url|#N> [concern]` analyses one held item and
recommends a ruling. It is read-only: it posts, edits, labels and
dispatches nothing, and its whole output is in this conversation. The
owner then rules with `verdict` (`verdict.md`).

## 0. Load

Step 0 (`SKILL.md`). An overlay problem stops `advise`: `<repo>` decides
what it may read, and `<design_entry>` where its principles come from.

## 1. Scope

- The input is an issue or PR URL, or `#N`, in `<repo>`. Refuse a URL in
  any other repository, naming `<repo>`: the rules and principles loaded
  here are not that repository's.
- Text after it is the owner's concern; the report answers it first.
- The item is as `verdict.md` (Scope) defines it. Read every member's
  thread, the brief and its dependencies' handoffs.
- An item without `need human` is analysed all the same, and the report
  says first that it is not held.

## 2. Check the evidence

Take the ruling request apart into its claims -- what the code does, what a
test shows, what the brief or a principle says -- and check each against
the code at the PR's head -- or, when the item has no PR, at a freshly
fetched `<remote>/<integration_branch>` -- and against the thread. Every
assertion in the report cites its source (`path: symbol`, a comment link, a
command and its result) or is marked unverified.

- Run read-only commands only. Run tests, in a `git archive` snapshot of
  that code, only when the decision hinges on their result.
- No experiment, edit, commit or comment, and no dispatched agent. A
  measurement the decision needs becomes an option: measure, then rule.
- Principles come only from `<design_entry>`, the documents it indexes,
  and `rules.md`. A principle found nowhere there is not one.

## 3. Report

In the conversation only, in this order:

1. **The question and the recommendation**, one line each.
2. **How it got stuck**: the events that led to the request, each linked.
3. **Why it needs the owner**: the escalation rule (`rules.md`,
   Escalations) that holds it, and whether the question still stands at
   the current head and thread. One already answered, or one an agent
   could settle as a finding, says so; the ruling then sends it back.
4. **The principles at stake**, each quoted with its source.
5. **Options**, one table: the option, its cost, the principles it keeps
   or breaks, its sources. The request's options first, then any this
   analysis adds, including a simpler one that keeps the same principles
   when there is one.
6. **The recommendation**, the fact that would change it, and a draft
   Ruling in `<publish_language>`, in `gh-prose`'s Ruling shape, linted as
   `--kind comment`:

   ```
   Ruling: (c) measure the gate at the head, then keep the cut if it is green. Splitting moves the same lines into two reviews.
   ```

A Mermaid UML diagram goes in only where text cannot carry the structure,
such as a dependency cycle across several items.

**Done when** every claim of the request is checked or marked unverified,
every option cites its sources, and the draft Ruling lints clean. `verdict`
then ranks this recommendation as `verdict.md` (Decide) says.
