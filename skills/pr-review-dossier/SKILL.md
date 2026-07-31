---
name: pr-review-dossier
description: Build a PDF dossier of a drafted PR review -- each comment with the source it points at, the precedent behind it, its failure scenario, a verdict, and a publish/reword/drop box with a reword note -- so you can judge every comment before it is published, then hand the marked-up PDF back to have the decisions applied. User-invoked: type /pr-review-dossier.
disable-model-invocation: true
---

# PR Review Dossier

A **dossier** is the case file assembled before a decision: for each drafted
review comment, everything needed to judge it -- the code it points at, the
precedent it invokes, what actually breaks, and how well it holds up. The user
reads the dossier, then decides which comments to publish.

The comment text alone is the thin end of this. A comment says *what*; the
dossier carries the *why*, and carries the code so the why can be checked
without leaving the page.

This skill is read-only and never posts to GitHub. Its only output is a PDF.

## Paths used below

- `<skill-dir>` -- the directory holding this `SKILL.md`, which is also where
  `pdf_forms.py` lives. Installed as a plugin that is
  `${CLAUDE_PLUGIN_ROOT}/skills/pr-review-dossier`; resolve it and use the real
  path rather than guessing.
- `<scratch>` -- a git-ignored scratch directory: the repository's own if it has
  one (for example `agent_space/`), otherwise a temporary directory outside the
  working tree. Dossiers are large and disposable; never leave them somewhere
  they could be committed.

## Inputs

The PR (URL or number) and the drafted review comments from `/pr-review-draft`.

If the user instead hands back a dossier PDF they have already marked up, skip
to [Step 6](#step-6----apply-a-marked-up-dossier) -- the work is reading their
decisions out of it, not building a new one.

Take the comments from the current session if they are there. Otherwise pull the
user's pending review from GitHub:

```bash
gh api repos/{owner}/{repo}/pulls/<PR>/reviews --jq '.[] | select(.user.login=="<me>" and .state=="PENDING") | {id, node_id}'
gh api repos/{owner}/{repo}/pulls/<PR>/reviews/<REVIEW_ID>/comments --jq '.[] | {path, line, body}'
```

If neither source has comments, stop and ask the user to run
`/pr-review-draft` first.

## Step 1 -- Assemble the case material

Collect the PR itself (`gh pr view <PR> --json title,body,author,url`,
`gh pr diff <PR>`) and the pr-explain briefing. If the briefing is not already
in the session, run the `pr-explain` skill on the PR now -- the dossier opens
with it, and the blast radius is what tells you which comments sit on
load-bearing code.

Give every drafted comment a stable ID (`C1`, `C2`, ...) and record its `path`,
`line`, category, and verbatim body.

**Done when:** every drafted comment has an ID and its verbatim text, and you
hold a full pr-explain briefing for the PR.

## Step 2 -- Build the record for each comment

This is the legwork the dossier exists for. Go back to the repository for each
comment -- the drafted text is the claim, not the evidence. Delegate comments to
parallel sub-agents when there are many.

Each comment's record carries:

1. **The code it points at** -- the whole enclosing function, class, or block as
   it reads *after* the change, quoted with real line numbers and the flagged
   line marked. Quote the diff hunk too when the change itself is the point.
   Enough context that the comment can be judged from the page alone.
2. **The precedent** -- the rule, pattern, or contract the comment invokes,
   backed by `file:line` evidence elsewhere in the repo where that pattern is
   already established, or the `CLAUDE.md`/`CONTRIBUTING.md` clause it rests on.
   Quote the precedent code, not just its path. When a search turns up no
   precedent, record that: a comment resting on nothing is exactly what the user
   wants to see before publishing.
3. **The failure scenario** -- concrete inputs, state, or configuration leading
   to the wrong behavior. For a design comment, the concrete cost paid later
   instead.
4. **The fix** -- what the author would change, named specifically.
5. **Blast-radius tie-in** -- the component or edge from the pr-explain diagrams
   this comment sits on, so its reach is visible.

**Done when:** every comment from Step 1 has all five, with each precedent and
failure scenario traced to code actually read in this run. A comment left
undocumented is the one the user publishes without understanding.

## Step 3 -- Verdict pass

For each comment, try to refute it: read the code again looking for the reason
the comment is wrong -- the guard that already exists elsewhere, the caller that
never hits the path, the convention that permits what was flagged. Then record:

- **Confirmed** -- the refutation attempt failed. State what was checked.
- **Speculative** -- the claim depends on something not verifiable from the code
  (author intent, runtime behavior, a downstream repo). State the dependency.
- **Refuted** -- the refutation succeeded. Keep the comment in the dossier with
  the refuting evidence; it is a candidate to drop.

**Done when:** every comment carries one of the three verdicts and the evidence
that produced it.

## Step 4 -- Render the dossier

Write the HTML, print it, then run the form pass -- both commands and the full
template are in [render.md](render.md).

Structure, front to back:

1. **Cover** -- PR title, number, URL, author, and the count of comments by
   verdict.
2. **Briefing** -- the pr-explain output entire: why, change walkthrough, review
   focus, and its diagrams **redrawn as inline SVG**. Terminal ASCII does not
   belong on a printed page; SVG prints as true vector.
3. **Comment index** -- one row per comment: ID, `path:line`, category, verdict,
   one-line summary, and `P`/`R`/`D` decision boxes. The survey before the
   detail, and the place to record a decision without leafing back.
4. **Comment cards** -- one page-broken card per comment, in index order,
   carrying the verbatim comment text plus all five parts from Step 2, the Step
   3 verdict with its evidence, a **Publish / Reword / Drop** decision box, and
   under it a **reword note** the user can type into: how this comment should be
   reworded, in their words.

Every comment's boxes appear twice -- index row and card -- and the form pass
turns each pair into one PDF field, so ticking either ticks both and the three
choices stay mutually exclusive. The reword note is a real PDF text field, and
Step 6 reads it back: a ticked Reword box says *change this*, the note says
*into what*, which is the difference between a decision the user has to explain
again in chat and one the dossier carries by itself.

Mark every block of drafted comment text as AI-generated.

Write both files to `<scratch>/`: `<scratch>/pr-<N>-dossier.html` and
`<scratch>/pr-<N>-dossier.pdf`.

**Done when:** every comment from Step 1 has a card, no card is split across a
page break, and the form pass reports three boxes and one reword note per
comment, in as many synced groups as there are comments.

## Step 5 -- Hand back

Report the PDF path, the verdict tally, and any comment whose precedent search
came up empty or that the Step 3 pass refuted -- the ones most likely to change
the user's publish decision.

Tell the user how to mark it up: tick P/R/D on each comment, and for anything
ticked Reword, type the rewording instruction in the note box on that comment's
page. Ticks and typed notes live only in a copy **saved from the PDF viewer**
(Ctrl+S in Chrome, Edge, or Acrobat) -- an unsaved viewer session loses both.
Handing that saved file back is what drives Step 6.

Nothing has been posted. Publishing stays with `/pr-review-draft`, on an
explicit request from the user.

## Step 6 -- Apply a marked-up dossier

Run when the user hands back the saved PDF -- usually a later session, so treat
the file as the source of truth over anything remembered about the comments.

```bash
python "<skill-dir>/pdf_forms.py" --read <scratch>/pr-<N>-dossier.pdf
```

Use this script; do not hand-roll a PDF parser. A viewer's save rewrites the
file with the field dictionaries inside compressed object streams, so a naive
regex over the raw bytes finds nothing -- or worse, finds the *pre-save*
revision and reports stale decisions. `--read` unpacks the object streams, takes
the definition latest in the file, and cross-checks each field's `/V` against
what its widgets actually paint (`/AS`); it exits rather than guess if the two
disagree. Two hand-written parsers on the same file can and do return two
different answers, and both look plausible.

The JSON gives every comment a `decision` (`Publish`, `Reword`, `Drop`, or
`null` for untouched) and a `note`. Then, per comment:

- **Publish** -- keep the verbatim text.
- **Reword** -- rewrite the comment to follow the note. The note is the
  instruction, not a suggestion; it outranks the drafted wording and this
  skill's own view of the comment. If a note asks for something the Step 2
  record contradicts -- a precedent it does not have, a claim the Step 3 pass
  refuted -- rewrite as asked and say what you found, rather than quietly
  softening the note.
- **Reword with an empty note** -- the user wants different wording but did not
  say how. Propose a rewrite and mark it as your guess; do not treat silence as
  approval of the original.
- **Drop** -- discard it, and do not resurrect it under a new ID.
- **null** -- undecided. List these back and ask; never publish one.

A reword instruction may also arrive in chat instead of the note field, and
often does when it is long or arrived before the note field existed. Treat it
exactly like a note: the file carries the decision, the user's words carry the
rewrite.

### Rewording that changes the ask, not the finding

The common reword is not "soften this" but "the finding is right and the
*remedy* is wrong". Keep the evidence -- the code quote, the precedent, the
failure scenario, the Step 3 verdict all still stand -- and replace only what
the comment asks the author to do.

A new remedy is a new claim, so verify it against the repository before writing
it, the same way Step 2 verified the original. If the note says *split these
files out*, run the split and quote the real numbers (`git diff --stat` on the
subset and on the remainder); if it says *drop this call site*, `git grep` what
else calls the thing and say plainly when the answer is nothing. Put whatever
the new remedy costs into the comment -- an unmentioned consequence the author
discovers on their own is what turns a scoping request into an argument.

Then re-read every **Drop** in light of it. Decisions the user made
independently often interact: a comment dropped on its own merits may also have
been made moot by a reword elsewhere, and comments pointing into the same file
as a now-removed change should not survive it. Say which is which, so a drop
that was a judgment call is not reported as a consequence.

Show the full revised set -- rewritten comments included -- and get explicit
approval of that exact text before anything reaches GitHub. Write it to
`<scratch>/pr-<N>-review-final.md` as well: the decisions came out of a PDF the
user may not still have open, and the final set is what a later session needs to
submit from.

Publishing itself stays with `/pr-review-draft`, which is also where the
one-pending-review-per-user rule is handled -- do not post from here.

**Done when:** every comment in the JSON is accounted for, every reworded
comment reflects its note, every new remedy was checked against the repo, the
knock-on effects between decisions are stated, and the user has approved the
final set verbatim.
