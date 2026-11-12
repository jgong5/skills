#!/usr/bin/env python3
"""A PR's state, read from its thread rather than from any summary.

Usage: pr_state.py PR [--repo OWNER/NAME]

Prints JSON: the last thread entry, the last verdict and the head it names,
the holds on landing, and whose turn it is (`land`, `developer`, `reviewer`,
or `held`). A verdict is a comment or review whose first line opens with
APPROVE or REQUEST CHANGES (markdown emphasis allowed) and names the head it
covers as a sha, as in `APPROVE @ 1a2b3c4.` A head the last verdict does
not cover is the reviewer's turn only once a later comment names it, as the
round comment `Round <k> pushed <sha>.` does; until then it is the developer's.
`verdicts` counts only the verdicts after the last Ruling -- an entry whose
first line opens with `Ruling:` or, for an AI ruling, `Ruling (auto):` -- so a
ruling restarts the count; the last verdict and holds still read the whole
thread. A REQUEST CHANGES that covers the head is the developer's turn. Any
entry after the last verdict whose first line opens a Ruling, or with
`Ruling on #N affects this:`, holds landing and makes a covered
head the reviewer's turn, even under an APPROVE: the ruling may have changed the
brief, or left nothing to push, so a fresh verdict under it comes first.
A brief update -- an entry with a line, or a sentence, opening with
`Brief updated:` outside inline code and fenced blocks -- after the last
verdict holds landing the same way, and while it follows the last comment
naming the head, the turn is the developer's: a changed brief is answered
with code, or with a round comment naming the unchanged head, before it is
reviewed.
A PR closed unmerged after this PR's first commit holds every turn when the
head descends from, or is, one of its commits: a stacked child whose parent
closed still carries the parent's unapproved commits, and once its base
reaches the integration branch the tree check would land them. A Ruling in
this thread after that close lifts the hold.
A caller may pass `equivalent(sha, head)` to let an APPROVE at another sha
cover the head; land.py does under --expect-tree.
"""

import argparse
import json
import re
import subprocess

# Each label's name, then its old name, still read for one version. LABEL
# holds every turn: agent-team/ruling holds for a ruling agent as
# need-human does for the owner. HOLD holds landing only; development and
# review go on.
LABEL = ("agent-team/need-human", "need human", "agent-team/ruling")
HOLD = ("agent-team/hold-landing", "hold landing")
# GitHub links closing keywords only on PRs into the default branch, so the
# body is read too, with every verb rules.md counts as delivering.
DELIVERS = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|address(?:es|ed)?|"
                      r"implement(?:s|ed)?)\s+#(\d+)")
VERDICT = re.compile(r"(APPROVE|REQUEST CHANGES)\b")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
RULED = re.compile(r"Ruling(?: \(auto\))?:")  # a Ruling, the owner's or an AI's
RULING = re.compile(RULED.pattern + r"|Ruling on #\d+ affects this:")
BRIEF = re.compile(r"(?m)(?:^\s*|[.!?]\s+)Brief updated:")
# A code span or fenced block: a backtick run up to the next run of the same length.
CODE = re.compile(r"(?s)(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)")
FIELDS = "number,state,body,headRefOid,headRefName,baseRefName,labels,comments,reviews,commits,closingIssuesReferences"


def gh(args, check=True):
    """Run gh; return stdout. With check=False a failure still returns the body gh printed."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def first_line(body):
    line = next((l for l in (body or "").splitlines() if l.strip()), "")
    return re.sub(r"^[\s#>*_]+", "", line).strip()


def thread(pr):
    """Every entry in time order: (time, kind, author, first line, whole body)."""
    entries = [(c["createdAt"], "comment", c["author"]["login"], first_line(c["body"]), c["body"] or "")
               for c in pr["comments"]]
    entries += [(r["submittedAt"], "review", r["author"]["login"], first_line(r["body"]), r["body"])
                for r in pr["reviews"] if r.get("submittedAt") and (r.get("body") or "").strip()]
    entries += [(c["committedDate"], "commit", "", c["oid"], "") for c in pr["commits"]]
    return sorted(entries)


def contains_commits_of(number, head, repo=None):
    """Whether `head` descends from, or is, a commit of PR `number`."""
    api = f"repos/{repo or '{owner}/{repo}'}"
    commits = gh(["api", "--paginate", f"{api}/pulls/{number}/commits", "--jq", ".[].sha"]).split()
    return any(gh(["api", f"{api}/compare/{c}...{head}", "--jq", ".status"]).strip() in ("ahead", "identical")
               for c in commits)


def state(number, repo=None, equivalent=None):
    r = ["-R", repo] if repo else []
    pr = json.loads(gh(["pr", "view", str(number), "--json", FIELDS, *r]))
    head = pr["headRefOid"]
    entries = thread(pr)
    verdicts = [e for e in entries if e[1] != "commit" and VERDICT.match(e[3])]
    ruled = max((i for i, e in enumerate(entries) if RULED.match(e[3])), default=-1)
    holds = []
    if pr["state"] != "OPEN":
        holds.append(f"PR is {pr['state']}")
    holds += [f"{name} on the PR" for name in LABEL + HOLD if name in {l["name"] for l in pr["labels"]}]
    issues = {i["number"] for i in pr["closingIssuesReferences"]}
    issues |= {int(n) for n in DELIVERS.findall(pr.get("body") or "")}
    for n in sorted(issues):
        labels = {l["name"] for l in json.loads(gh(["issue", "view", str(n), "--json", "labels", *r]))["labels"]}
        holds += [f"{name} on issue #{n}, which this PR delivers" for name in LABEL + HOLD if name in labels]
    first = min((c["committedDate"] for c in pr["commits"]), default=None)
    closed = json.loads(gh(["pr", "list", "--state", "closed", "--search", f"is:unmerged closed:>{first}",
                            "--json", "number,closedAt", "--limit", "1000", *r])) if first else []
    lifted = entries[ruled][0] if ruled >= 0 else ""
    orphaned = [f"contains commits of #{a['number']}, closed unmerged" for a in closed
                if a["number"] != pr["number"] and a["closedAt"] > lifted
                and contains_commits_of(a["number"], head, repo)]
    holds += orphaned
    verdict = None
    if verdicts:
        at, _, author, line, _ = verdicts[-1]
        sha = SHA.search(line)
        verdict = {"verdict": VERDICT.match(line).group(1), "sha": sha and sha.group(0),
                   "author": author, "at": at, "line": line}
    covers = bool(verdict and verdict["sha"] and (head.startswith(verdict["sha"]) or (
        equivalent and verdict["verdict"] == "APPROVE" and equivalent(verdict["sha"], head))))
    if not verdict:
        holds.append("no verdict yet")
    elif not verdict["sha"]:
        holds.append("the last verdict names no sha")
    elif not covers:
        need = "delta review needed" if verdict["verdict"] == "APPROVE" else "review the whole head"
        holds.append(f"the last verdict covers {verdict['sha']}, head is {head[:12]}: {need}")
    elif verdict["verdict"] != "APPROVE":
        holds.append(f"the last verdict is REQUEST CHANGES @ {verdict['sha']}")
    last_verdict = entries.index(verdicts[-1]) if verdicts else -1
    since = entries[last_verdict + 1:]
    named = [i for i, (_, kind, _, line, _) in enumerate(since)
             if kind == "comment" and any(head.startswith(s) for s in SHA.findall(line))]
    briefed = [i for i, e in enumerate(since) if BRIEF.search(CODE.sub("code", e[4]))]
    ruled_since = any(kind != "commit" and RULING.match(line) for _, kind, _, line, _ in since)
    if ruled_since:
        holds.append("a ruling follows the last verdict")
    if briefed:
        holds.append("a brief update follows the last verdict")
    if not covers and not named:
        holds.append(f"head {head[:12]} has no round comment")
    if pr["state"] != "OPEN" or orphaned or any(h.startswith(LABEL) for h in holds):
        turn = "held"
    elif briefed and briefed[-1] > max(named, default=-1):
        turn = "developer"
    elif covers and verdict["verdict"] == "APPROVE" and not (ruled_since or briefed):
        turn = "held" if any(h.startswith(HOLD) for h in holds) else "land"
    elif covers:
        turn = "reviewer" if ruled_since or briefed else "developer"
    else:
        turn = "reviewer" if named else "developer"
    last = entries[-1] if entries else None
    return {
        "pr": pr["number"], "state": pr["state"], "head": head, "branch": pr.get("headRefName"),
        "base": pr["baseRefName"],
        "last_entry": last and dict(zip(("at", "kind", "author", "line"), last)),
        "verdict": verdict, "verdicts": sum(e in verdicts for e in entries[ruled + 1:]),
        "holds": holds, "turn": turn,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo")
    a = ap.parse_args()
    print(json.dumps(state(a.pr, a.repo), indent=1))
