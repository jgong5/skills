---
name: auto-grilling
description: Grills a plan by answering every question itself with its recommended answer, logs each decision to a <topic>.grill.md, and stops once, at a final action menu (write a document, write code, /agent-team plan, revise, end). User-invoked: /auto-grilling <plan text | file path>.
disable-model-invocation: true
---

# auto-grilling

Stress-test a plan the way a relentless interviewer would -- walk every
branch of its decision tree, resolving dependencies one decision at a time
-- but answer each question yourself with your recommended answer, and keep
going until the tree is done. The user is asked exactly once, at the end.

Adapted from Matt Pocock's
[`grilling`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling)
skill, MIT licensed ([license](https://github.com/mattpocock/skills/blob/main/LICENSE),
Copyright (c) 2026 Matt Pocock). This is a rewrite, not a wrapper: `grilling`
says to ask one question at a time and wait for the user's answer to each,
and those lines contradict a run that never waits. Invoking it and
overriding them would leave two instructions fighting in one context.

## Input

`/auto-grilling <plan text | file path>`. A path is read; anything else is
the plan itself. Read the code and documents the plan touches before the
first question, because a question the environment can answer is not a
question.

Talk to the user, and write `.grill.md`, in the user's language; this file
stays English so one copy serves every user.

## The run

Never stop mid-run. A pause to ask is exactly the cost this skill exists to
remove; a doubtful answer is instead tagged `low` and shown at the end,
where the user can overturn it with the whole tree in view.

For each question, in dependency order:

1. **Look up what can be looked up.** A fact in the filesystem, the code, a
   tool's output or `--help` is checked, never assumed. Only decisions get
   answered.
2. **Answer with your recommendation**, and name the **strongest rejected
   alternative** and why it lost, in one line. If no alternative is
   credible, the question decides nothing: merge it into a neighbour or skip
   it. A decision with no real rival is noise in the log.
3. **Set confidence** to `high` or `low`. It is `low` when any of these
   holds, `high` otherwise:
   - the answer rests on a user preference or an external constraint the
     environment cannot reveal (a deadline, a team convention, a budget);
   - the rejected alternative is about as strong as the answer;
   - the answer rests on a factual assumption you could not verify.
   Two levels, because a finer scale invites arguing over the scale; the
   only question at the end is "should the user look at this one?".
4. **Record it**: append the entry to `.grill.md` at once, and echo one line
   in chat, `Q7 [high] B: <reason>` -- number, confidence, the answer in a
   few words, the reason. Appending as you go means an interrupted run
   leaves a usable log, and the chat line lets the user watch the run
   without reading the file.

New branches the answers open join the queue. **Hard cap: 40 questions per
run.** A plan that needs more is too big for one sitting; list each branch
still open at the cap as `unresolved` in the summary rather than answering
it in a hurry.

**Done when** the summary can name the deliverable, its scope and non-goals,
the change per module or file, and how it is accepted -- and no open
question would change the deliverable. Those four are what a design
document needs, and what `/agent-team plan` needs to cut a task graph.

## `<topic>.grill.md`

`<topic>` is a short kebab-case name for the plan. Put the file in the
project's git-ignored scratch directory when it has one (named in its
`CLAUDE.md`, or an existing directory `git check-ignore` reports as
ignored), else in the working directory. Scratch first, because the log is
working material, not something to commit by accident.

```
# Grill: <topic>
Input: <path, or "inline plan">

## Decisions
### Q<n>. <question>
- Answer: <the recommended answer>
- Reason: <why>
- Rejected: <strongest alternative> -- <why it lost>
- Confidence: high | low | human
- Depends on: Q<m>, ... | none

## Summary
- Deliverable:
- Scope / non-goals:
- Changes: <one line per module or file>
- Acceptance:
- Low confidence: Q<n> <one line>, ... | none
- Unresolved: <branches open at the cap> | none
```

`Depends on` is what makes a revision cheap: it says exactly which answers
a changed decision invalidates.

## The final menu

Show the summary's `low` decisions, one line each, then a numbered text
menu, recommended item first and marked as such. It is a text menu, not
`AskUserQuestion`, because it can carry more options than that tool takes.
Then wait -- this is the one stop.

- **Write a document**: a design document from the summary, at a path you
  name in the menu line.
- **Write code in this session**: implement the summary now.
- **`/agent-team plan`** with `.grill.md` as the design document. Print the
  exact command for the user to run: `agent-team` is user-invoked only, so
  you cannot start it yourself.
- **Revise a decision** (below).
- **End**, keeping only `.grill.md`.

Recommend `/agent-team plan` for a GitHub project with a large change
(about 300 lines or more, or several modules); writing code here for a
small change; a document when no code changes. Offer `/agent-team plan` at
all only when all three hold, because otherwise it fails on its first step:

- `git remote -v` shows a GitHub remote;
- `gh auth status` succeeds;
- `agent-team` is installed: `claude plugin list` shows an enabled plugin
  that ships it, or a `.claude/skills/agent-team/SKILL.md` exists in the
  project or home directory. The session's skill list cannot tell you, since
  user-invoked skills are hidden from it.

Run these the way the project's `CLAUDE.md` says to run commands (a
container wrapper, say), plainly where it says nothing.

## Revise

The user names a decision in chat, or edits `.grill.md` and says so; reread
the file and treat every entry whose answer changed as named.

1. Each named decision takes the user's answer and confidence `human`. A
   `human` decision is never auto-answered again, in this run or a later
   revision: the user has spoken, and overriding them is the one thing this
   skill must not do.
2. Every decision that depends on it, transitively through `Depends on`, is
   invalidated and re-derived in place under its own number; new branches
   it opens are appended. Decisions outside that set are kept as they are,
   because nothing they rest on changed.
3. The 40-question cap restarts for this pass.
4. Rewrite the summary, then show the menu again, with the `human`
   decisions listed as their own group above the `low` ones.

Entries are rewritten in place rather than kept as history because
`.grill.md` doubles as the design document: a superseded entry left in it
reads as a live decision.
