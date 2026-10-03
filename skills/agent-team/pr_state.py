#!/usr/bin/env python3
"""A PR's state, read from its thread rather than from any summary.

Usage: pr_state.py PR [--repo OWNER/NAME]

Prints JSON: the last thread entry, the last verdict and the head it names,
the holds on landing, and whose turn it is (`land`, `developer`, `reviewer`,
or `held`). A verdict is a comment or review whose first line opens with
APPROVE or REQUEST CHANGES (markdown emphasis allowed) and names the head it
covers as a sha, as in `APPROVE @ 1a2b3c4.`
"""

import argparse
import json
import re
import subprocess

LABEL = "need human"
# GitHub links closing keywords only on PRs into the default branch, so the
# body is read too, with every verb rules.md counts as delivering.
DELIVERS = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|address(?:es|ed)?|"
                      r"implement(?:s|ed)?)\s+#(\d+)")
VERDICT = re.compile(r"(APPROVE|REQUEST CHANGES)\b")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
FIELDS = "number,state,body,headRefOid,baseRefName,labels,comments,reviews,commits,closingIssuesReferences"


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
    """Every entry in time order: (time, kind, author, first line)."""
    entries = [(c["createdAt"], "comment", c["author"]["login"], first_line(c["body"]))
               for c in pr["comments"]]
    entries += [(r["submittedAt"], "review", r["author"]["login"], first_line(r["body"]))
                for r in pr["reviews"] if (r.get("body") or "").strip()]
    entries += [(c["committedDate"], "commit", "", c["oid"]) for c in pr["commits"]]
    return sorted(entries)


def state(number, repo=None):
    r = ["-R", repo] if repo else []
    pr = json.loads(gh(["pr", "view", str(number), "--json", FIELDS, *r]))
    head = pr["headRefOid"]
    entries = thread(pr)
    verdicts = [e for e in entries if e[1] != "commit" and VERDICT.match(e[3])]
    holds = []
    if pr["state"] != "OPEN":
        holds.append(f"PR is {pr['state']}")
    if LABEL in {l["name"] for l in pr["labels"]}:
        holds.append(f"{LABEL} on the PR")
    issues = {i["number"] for i in pr["closingIssuesReferences"]}
    issues |= {int(n) for n in DELIVERS.findall(pr.get("body") or "")}
    for n in sorted(issues):
        labels = json.loads(gh(["issue", "view", str(n), "--json", "labels", *r]))["labels"]
        if LABEL in {l["name"] for l in labels}:
            holds.append(f"{LABEL} on issue #{n}, which this PR delivers")
    verdict = None
    if verdicts:
        at, _, author, line = verdicts[-1]
        sha = SHA.search(line)
        verdict = {"verdict": VERDICT.match(line).group(1), "sha": sha and sha.group(0),
                   "author": author, "at": at, "line": line}
    covers = bool(verdict and verdict["sha"] and head.startswith(verdict["sha"]))
    if not verdict:
        holds.append("no verdict yet")
    elif not verdict["sha"]:
        holds.append("the last verdict names no sha")
    elif not covers:
        holds.append(f"the last verdict covers {verdict['sha']}, head is {head[:12]}: delta review needed")
    elif verdict["verdict"] != "APPROVE":
        holds.append(f"the last verdict is REQUEST CHANGES @ {verdict['sha']}")
    if pr["state"] != "OPEN" or any(LABEL in h for h in holds):
        turn = "held"
    elif covers:
        turn = "land" if verdict["verdict"] == "APPROVE" else "developer"
    else:
        turn = "reviewer"
    last = entries[-1] if entries else None
    return {
        "pr": pr["number"], "state": pr["state"], "head": head, "base": pr["baseRefName"],
        "last_entry": last and dict(zip(("at", "kind", "author", "line"), last)),
        "verdict": verdict, "verdicts": len(verdicts), "holds": holds, "turn": turn,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo")
    a = ap.parse_args()
    print(json.dumps(state(a.pr, a.repo), indent=1))
