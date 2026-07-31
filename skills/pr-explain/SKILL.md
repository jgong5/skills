---
name: pr-explain
description: Explain a pull request (given its URL or number) so a reviewer can understand it fast, covering the change itself, its blast radius across other modules, the motivating context, and the global picture via terminal-rendered architecture and data/control flow diagrams. Use when the user wants to understand a PR, asks to "explain this PR", "walk me through this PR/change", "help me review this PR", or wants the big picture of a change before reviewing.
---

# Explain a PR for Review

Turn a PR into a review briefing: not a line-by-line diff summary, but the
picture a reviewer needs before reading a single line. The core work is tracing
the change's **blast radius** -- everything it touches beyond the diff -- and
drawing that picture. A diff can be read locally; the interactions cannot. This
skill exists to surface the interactions.

This skill is read-only. Deliver the briefing to the user in-chat (or write it
to a file if asked). Never post it to GitHub.

## Inputs

A PR URL or number. If none is given, stop and ask for one. Default the repo to
the current one unless the URL points elsewhere.

## Step 1 -- Pull the PR and its why

```bash
gh pr view <PR> --json title,body,author,baseRefName,files,additions,deletions,commits,url
gh pr diff <PR>
```

Read the description and any linked issue (`gh issue view <N>`) for the
motivation. The diff says *what*; the description and issue say *why* -- capture
both.

**Done when:** you can state the PR's purpose in one sentence and you have the
full list of changed files and the changed symbols within them (functions,
classes, methods, configs, public APIs).

## Step 2 -- Trace the blast radius

For every changed symbol from Step 1, find what it connects to in the wider
codebase. Use Grep/Glob across the repo; for a large surface, delegate symbols
to parallel subagents.

For each changed symbol, identify:
- **Upstream** -- who calls it, instantiates it, or depends on its behavior.
- **Downstream** -- what it calls, the modules/components it reaches into.
- **Siblings** -- overrides, subclasses, other implementations of the same
  interface, and the tests that exercise it.
- **Dead or duplicated** -- symbols added but never referenced anywhere (dead
  until a later change wires them), and logic copy-pasted across two or more
  changed files instead of shared. Both are prime review targets; flag them.

**Done when:** every changed symbol has its upstream and downstream accounted
for, or is explicitly marked self-contained. A symbol left untraced is the
interaction a reviewer will miss -- do not skip.

## Step 3 -- Draw the global picture

Produce two plain-ASCII diagrams that render in any terminal -- no Mermaid, no
image formats. See `diagrams.md` for the box/tree/flow recipes.

- **Architecture diagram** -- the components/modules in the blast radius and how
  they relate. Mark the changed ones (e.g. a `*` tag).
- **Data/control flow diagram** -- the execution path through the changed code,
  end to end, marking where behavior changed.

**Done when:** every component from the Step 2 blast radius appears on the
architecture diagram, and the changed execution path appears end-to-end on the
flow diagram.

## Step 4 -- Write the briefing

Structure it outside-in, so the reviewer builds context before hitting code:

1. **Why** -- motivation and the problem being solved (from Step 1).
2. **Global picture** -- the two diagrams, each with a short paragraph reading it
   out.
3. **Change walkthrough** -- group the diff by logical change (not by file).
   For each group: what changed, why, and which interactions from the blast
   radius it affects. Tie each group back to a node/edge in the diagrams.
4. **Review focus** -- where to scrutinize: risky interactions, edge cases,
   backward-compatibility, and anything the blast radius flagged as fragile.

**Done when:** every changed file is referenced somewhere in the walkthrough,
and both diagrams are referenced from the prose.
