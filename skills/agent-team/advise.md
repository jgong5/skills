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
assertion in the report's Evidence part cites its source (`path: symbol`, a
comment link, a command and its result); one left unchecked is marked
unverified wherever the report uses it.

- Run read-only commands only. Run tests, in a `git archive` snapshot of
  that code, only when the decision hinges on their result.
- No experiment, edit, commit or comment, and no dispatched agent. A
  measurement the decision needs becomes an option: measure, then rule.
- Principles come only from `<design_entry>`, the documents it indexes,
  `rules.md`, and the overlay body. A principle found nowhere there is not
  one. The local body is environment fact, never a principle, so one item
  gets the same recommendation on every checkout.

## 3. Report

In the conversation only, after the answer to the owner's concern and the
notice that the item is not held (Scope). The owner rules from the
overview; a history of the request, or a list of every claim checked, reads
as a work log and buries the decision.

1. **Overview**, in plain words and without citations, enough to rule from
   alone:
   - the question;
   - the current state: the mechanism that keeps the item stuck and the
     change that triggered it, linked -- no timeline;
   - the options, one sentence each: what it does, what it gains, what it
     costs; one this analysis adds is marked new;
   - the recommendation and why;
   - side findings that need no ruling, when there are any, one sentence
     each: what it is, and who can fix it or that the recommended option
     does.

   A question that no longer stands in the code step 2 checked and the
   thread, or that an agent could settle as a finding, is said first; the
   recommendation is then to send it back.
2. **Evidence**:
   - the principles at stake, each quoted with its source;
   - the options in one table: the option, its cost, the principles it
     keeps or breaks, its sources. The request's options first, then any
     this analysis adds, including a simpler one that keeps the same
     principles when there is one. A claim of the request found wrong is
     stated in the row of the option it bears on;
   - the fact that would change the recommendation;
   - a draft Ruling in `<publish_language>`, in `gh-prose`'s Ruling shape,
     linted as `--kind comment`:

     ```
     Ruling: (c) measure the gate at the head, then keep the cut if it is green. Splitting moves the same lines into two reviews.
     ```

Step 2 checks every claim of the request; the report lists none of them.

A Mermaid UML diagram goes in only where text cannot carry the structure,
such as a dependency cycle across several items.

**Done when** every claim of the request is checked or marked unverified,
every option cites its sources, and the draft Ruling lints clean. `verdict`
then ranks this recommendation as `verdict.md` (Decide) says.
