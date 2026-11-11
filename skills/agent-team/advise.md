# advise: why a held item is stuck, and what to rule

`/agent-team advise <url|#N> [concern]` analyses one held item and
recommends a ruling. It is read-only: it posts, edits, labels and
dispatches nothing, and its whole output is in this conversation. It runs
for anyone; the item's ruler (`rules.md`, Escalations) then rules with
`verdict` (`verdict.md`).

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
- Precedents: search `<repo>`'s issues and PRs, comments included, for
  `Ruling:` with the files, symbols and terms the item touches
  (`gh search issues --include-prs`). An owner who remembers ruling on
  something like this has to ask otherwise, because related items rarely
  link each other. A Ruling binds its own item; elsewhere it weighs less
  than a principle, and where the two disagree the report says so.
- Go back to the goal before taking the request's options: find what the
  item serves in its brief or the design documents, and ask in order
  whether the effect is real -- not an artifact of the measurement, nor a
  bug in this code or a dependency -- whether the goal needs the work at
  all, and what the least code that reaches the goal is. The cheapest
  rulings come from these questions, not from shortening the request's
  own option, and the request rarely asks them of itself.
- Put each option's gain and cost in numbers, in the units the item turns
  on: code lines, GPU or machine hours, the error or accuracy before and
  after, runtime overhead. Note where each was measured -- which models and
  platforms -- and what is inferred beyond them.

## 3. Report

In the conversation only. Its first line names the item's ruler, as
`python3 <skill-dir>/ruler.py N --repo <repo>` prints it, or says it has
none; then come the answer to the owner's concern and the notice that the
item is not held (Scope). The ruler rules from the overview; a history of the request, or a list of every claim checked, reads
as a work log and buries the decision.

1. **Overview**, in plain words and without citations, enough to rule from
   alone by a ruler who has not looked at the item in days:
   - what the item is for, in one sentence, then the question;
   - the current state: the mechanism that keeps the item stuck and the
     change that triggered it, linked -- no timeline. Its causes ranked by
     their share, the main one named; when no measurement has established
     the cause, the state says so first, and one option is to measure it,
     naming what and roughly how many machine hours;
   - the options, one sentence each: what it does, what it gains, what it
     costs, in step 2's numbers, and where it holds. One this analysis
     adds is marked new; one that answers a different question than the
     request asked, from going back to the goal, is marked reframed. The
     least-code option is always listed, recommended or not;
   - the recommendation and why, with a worked example by hand when it
     rests on a formula or an algorithm;
   - the precedents step 2 found that bear on it, one sentence each; one
     the recommendation departs from is named, with whether it overturns
     that Ruling, and why, or how this item differs;
   - side findings that need no ruling, when there are any, one sentence
     each: what it is, and who can fix it or that the recommended option
     does.

   The ruler reads only this part, so it is written for someone without
   the context: each project term is glossed in half a sentence where it
   first appears; each number names its base -- a share of what, over
   which window, on which machine; another issue or Ruling gets a phrase
   saying what it is. Each key number or causal claim carries one tag:
   measured (on what), derived (from what), or the request's, unverified.
   A misread number turns a ruling; an unexplained one only costs a
   question.

   When the mechanism has an order in time or several parties -- host and
   device, ranks, threads, processes -- a Mermaid `sequenceDiagram` shows
   it in place of the text that would describe it, and an option that
   changes that flow gets one of its own. Keep each small (about six
   participants and fifteen messages) and plain: no `rect`, no `<br/>`,
   no nested blocks, which some renderers print as source. A static
   question -- a rename, a line count, a missing brief field -- gets none.

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
     linted as `--kind comment`, that calls for its follow-ups so `verdict`
     (step 4) carries them out: a tracking issue for each problem the
     ruling defers and each side finding no option fixes, with a suggested
     label and assignee -- the item's own, or one the thread says can
     reach the environment the work needs; and, when the recommended
     option is a simplification or a stopgap, a note in the docs or code
     saying so and what it costs. The ruler strikes what they do not want;
     a problem left without an issue is forgotten.

     ```
     Ruling: (c) measure the gate at the head, then keep the cut if it is green. Splitting moves the same lines into two reviews. Track the flaky warmup in a new issue, assigned like this one.
     ```

Step 2 checks every claim of the request; the report lists none of them.

**Done when** every claim of the request is checked or marked unverified,
every option cites its sources and states its numbers, the precedents are
searched, and the draft Ruling lints clean. `verdict`
then ranks this recommendation as `verdict.md` (Decide) says.
