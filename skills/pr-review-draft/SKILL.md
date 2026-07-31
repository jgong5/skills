---
name: pr-review-draft
description: Full PR review that surfaces a pr-explain briefing to you first and, on request, posts findings as a GitHub draft (pending) review; publishes only when explicitly asked to. User-invoked: type /pr-review-draft.
disable-model-invocation: true
---

# PR Review (context-first, draft-submit)

A wrapper around your installed `pr-review` skill, with two changes:

1. Build context with a **pr-explain** briefing before reviewing.
2. Submit findings as a **draft** (pending) review; publish only when the user
   explicitly asks you to publish.

Everything else -- philosophy, checklist, backward-compatibility rules,
fact-check, output format -- lives in `pr-review`. Do not restate or reinvent
any of it here; invoke that skill and follow it.

## Prerequisite

This skill requires a `pr-review` skill to be available in the session. Many
repositories ship one under `.claude/skills/pr-review/`, carrying that project's
own review standards. If no `pr-review` skill is available, say so and stop --
do not substitute a generic review, because the project-specific checklist is
the whole point of delegating to it.

## Scratch files

Where this skill writes intermediate files (`<scratch>/` below), use a
git-ignored scratch directory: the repository's own if it has one (for example
`agent_space/`), otherwise a temporary directory outside the working tree. Never
leave intermediate files where they could be committed.

## Step 1 -- Context briefing (pr-explain)

Invoke the `pr-explain` skill on the target PR and dump its full briefing (why,
blast radius, diagrams, review focus) to the user in chat before you read the
diff. Carry the blast radius into the review: it names which changed lines are
load-bearing and where to spawn investigation sub-agents.

**Done when:** the complete pr-explain briefing has been delivered to the user
and you can state the PR's purpose and its riskiest interactions.

## Step 2 -- Review

Invoke the `pr-review` skill and follow it end to end -- its usage modes, review
philosophy, review workflow (including whatever checklist and
backward-compatibility guidance it references), fact-check, and output format.
Feed the Step 1 briefing in as its "understand the context" input, so
investigation targets the interactions pr-explain surfaced.

**Done when:** you have a review in that skill's output format, fact-checked per
its own verification step.

## Step 3 -- Submit (draft unless publishing is asked for)

Only when the user asks you to submit, post, or leave comments on the PR.
Delivering the review in chat (Step 2) never posts anything.

A submission from this skill is a **draft** -- a GitHub *pending* review that
stays private until the user clicks Submit in the GitHub UI -- unless the user
asks in their own words for a published one. Publishing is irreversible: a
posted review notifies the PR author and cannot be recalled. When in doubt,
draft it; a draft the user wanted published costs one click, the reverse costs
nothing less than a retraction.

**Content approval is not permission to publish.** These are two separate
questions and the disclosure gate below only ever asks the first:

- *Is this text right?* -- the gate. Answering yes, including with a bare
  "approve", "lgtm", "yes", or "go ahead", approves **what the draft says**.
  It never escalates a draft to a published review.
- *Should this be published?* -- a request the user makes unprompted, naming
  the act of publishing: "publish it", "submit it for real", "post a formal
  review", "leave an approving review", "request changes on it".

Approval of content is the far more common case, so read an ambiguous go-ahead
as answering the first question. Escalate only on an unmistakable instance of
the second. If it is genuinely unclear which the user meant, ask -- do not guess
toward publishing.

When publishing *is* asked for, use the same call with `event` added:
`"COMMENT"`, `"APPROVE"`, or `"REQUEST_CHANGES"` -- matching what the user
asked for, defaulting to `"COMMENT"` if they did not say. State plainly in chat
that this posts publicly and is not undoable before you run it.

Always post each finding as an **embedded comment**: an inline comment anchored
to its `path`/`line` in the diff, not prose folded into the review body. The body
holds only the overall summary; every line-specific finding is an inline comment.
Mark every comment with a `by AI agent` note so nothing reads as human-written.

**Dedup against existing comments (mandatory):** before submitting, pull the
comments already on the PR and drop any finding an existing one already covers --
same file/line raising the same point, even if worded differently. Never submit
a duplicate.

```bash
gh api repos/{owner}/{repo}/pulls/<PR>/comments   # inline review comments
gh pr view <PR> --json comments                    # top-level PR comments
```

Submit only the surviving (non-duplicate) findings. Dump the dropped duplicates
to the user as a reference -- each with the existing comment it duplicates -- so
they can see what was skipped and why.

When presenting the draft for approval, mention that `/pr-review-dossier` builds
a PDF case file for these comments -- each one with its source, precedent,
failure scenario and verdict -- if the user wants to study them before deciding.

**AI-disclosure gate (mandatory):** before any `gh` call that writes to GitHub,
show the user the exact review body and every inline comment, and get explicit
approval of that content. Wrap the AI-generated text in a code or quote block.
No autonomous posting, ever. If the repository has its own AI-contribution
policy (`AI_POLICY.md`, `CONTRIBUTING.md`, or similar), read it and comply with
that too -- some projects impose stricter labelling, or forbid agent-posted
review comments outright.

A pending review carries inline comments and omits `event`:

```bash
# Write review.json under your scratch directory:
# {"body": "...overall summary...",
#  "comments": [{"path": "src/foo.py", "line": 42, "side": "RIGHT", "body": "..."}]}
# Omitting "event" makes the review PENDING (a draft).
gh api -X POST repos/{owner}/{repo}/pulls/<PR>/reviews --input <scratch>/review.json
```

- `{owner}/{repo}` fill from the current repo; set `GH_REPO=owner/repo` if the
  PR lives elsewhere.
- `line` must be a line the diff touches on the `RIGHT` (new) side; for a
  deleted line use `"side": "LEFT"`.
- `event` is what separates a draft from a published review. Before running the
  command, verify the JSON's `event` key matches what the user actually asked
  for -- absent for a draft, present only on an explicit request to publish.

### Adding comments to an existing pending review (GraphQL)

GitHub allows only **one pending review per user per PR**, and the REST
`POST .../pulls/<PR>/reviews` call *creates* a review -- so if the user already
has a pending review open (e.g. one they started in the UI, or one you created
earlier in the session), that call fails with
`422 "User can only have one pending review per pull request."` REST has no
endpoint to append a comment to an existing pending review
(`.../reviews/{id}/comments` is read-only).

**Always list the user's pending reviews before the REST POST**, not after it
fails -- discovering the conflict from a 422 invites fixing it the wrong way
under time pressure.

Do **not** solve this by deleting and recreating the review. That risks
clobbering comments the user authored, and "the existing review looked empty"
is not a sufficient reason: an empty-bodied review with no comments still may be
one the user just started in the UI and is mid-way through, and the GraphQL
append below works on it either way at no extra cost. Delete only if the user
says to, and report it if you do. Instead use the GraphQL
`addPullRequestReviewThread` mutation, which attaches a new inline thread
directly to the existing pending review by its node ID:

```bash
# 1. Get the pending review's GraphQL node id (REST id -> node_id).
gh api repos/{owner}/{repo}/pulls/<PR>/reviews/<REVIEW_ID> --jq '{node_id, state}'

# 2. Add each finding as a thread on that review. Repeat per comment.
gh api graphql -f query='
mutation($reviewId: ID!, $path: String!, $line: Int!, $body: String!) {
  addPullRequestReviewThread(input: {
    pullRequestReviewId: $reviewId, path: $path, line: $line,
    side: RIGHT, body: $body
  }) { thread { id line path } }
}' -F reviewId="<NODE_ID>" -F path="src/foo.py" -F line=42 -F body="..."
```

- Find the existing pending review first:
  `gh api repos/{owner}/{repo}/pulls/<PR>/reviews --jq '.[] | select(.user.login=="<me>") | {id, state}'`
  (`gh api user --jq .login` for `<me>`). Only a `PENDING` review blocks a new one.
- If no pending review exists, prefer the single REST `reviews` POST above
  (one call, atomic). Use GraphQL only to add to a review that already exists.
- The same disclosure gate applies: show the exact per-comment bodies and get
  approval before any of these mutations run.

### Verify the review after creating it

A pending review's comments are invisible to `GET .../pulls/<PR>/comments` --
that endpoint only lists comments on *submitted* reviews, so an empty result
there proves nothing. Read the review's own endpoint instead:

```bash
gh api repos/{owner}/{repo}/pulls/<PR>/reviews/<REVIEW_ID>/comments \
  --jq '.[] | "\(.path)  pos=\(.position)  [\(.body|length) chars]"'
```

`line`, `original_line` and `side` all come back `null` on a pending comment;
GitHub resolves them at submit time. A non-null `position` is the signal the
anchor was accepted. Confirm the count matches what you posted, and confirm
`commit_id` on the review still equals the PR's `headRefOid` -- if the author
pushed while you were drafting, the anchors are against a stale commit.

Note `gh api` in Git Bash mangles a leading-slash endpoint into a filesystem
path (`invalid API endpoint: "C:/.../repos/..."`). Write endpoints without the
leading slash: `repos/{owner}/{repo}/...`.

**Done when:** only non-duplicate findings were submitted, each as an embedded
inline comment marked `by AI agent`; the dropped duplicates were dumped to the
user; the review's state matches what the user asked for -- `PENDING` for a
draft, with the user told to finish it in the GitHub UI, or published only on an
explicit request to publish; and nothing was posted without content approval.
