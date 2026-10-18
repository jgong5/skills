#!/usr/bin/env python3
"""Land a batch of approved PRs, gated once as one tree.

Usage: batch.py merge PR... --record FILE
       batch.py land --record FILE --message-dir DIR

Run from inside the repository. `merge` merges each approved head onto the
integration tip in the order given, as local commits it never pushes, writes
each PR's approved sha, merge base and tree to FILE, and prints the final
commit for <gate_task>. `land` lands FILE's PRs in order through land.py,
DIR/<pr>.txt as each message, patching an unlinked child's base and pushing
a base update wherever GitHub's own merge would not give the recorded tree.
A merged PR is skipped, so a rerun resumes. Exits as land.py does.
"""

import argparse
import json
import re
import time
from pathlib import Path

import land
import overlay
import pr_state
from land import git, stop

POLLS, POLL = 12, 5  # GitHub retargets and rebases a linked child within seconds
ROUND = re.compile(r"Round (\d+) pushed")


def view(repo, n):
    return json.loads(pr_state.gh(["pr", "view", str(n), "-R", repo, "--json",
                                   "state,baseRefName,headRefOid,headRefName,comments"]))


def stack_of(repo, n):
    """The other PRs linked with `n` in a GitHub stack."""
    out = pr_state.gh(["api", f"repos/{repo}/stacks?pull_request={n}"], check=False)
    stacks = json.loads(out or "[]")
    return sorted({p["number"] for s in stacks if isinstance(s, dict)
                   for p in s.get("pull_requests", [])} - {n})


def merge(keys, prs, record):
    repo, branch = keys["repo"], keys["integration_branch"]
    states = [pr_state.state(n, repo) for n in prs]
    held = [f"#{s['pr']}: turn {s['turn']}; {'; '.join(s['holds'])}" for s in states
            if s["turn"] != "land"]
    if held:
        stop(3, "hold:\n" + "\n".join(held))
    rc, out = git("fetch", "-q", keys["remote"], f"+refs/heads/{branch}:{land.TIP}",
                  *[f"refs/pull/{n}/head" for n in prs])
    if rc:
        stop(4, f"fetch failed: {out}")
    tip = commit = git("rev-parse", land.TIP)[1]
    bases, rows = {branch}, []
    for s in states:
        if s["base"] not in bases:
            stop(3, f"hold: #{s['pr']} is based on {s['base']}, which nothing before it lands")
        bases.add(s["branch"])
        base = git("merge-base", commit, s["head"])[1]
        rc, out = git("merge-tree", "--write-tree", commit, s["head"])
        if rc:
            stop(4, f"#{s['pr']} conflicts with the batch below it:\n{out}")
        tree = out.splitlines()[0]
        commit = git("commit-tree", tree, "-p", commit, "-p", s["head"], "-m", f"batch #{s['pr']}")[1]
        rows.append({"pr": s["pr"], "sha": s["head"], "branch": s["branch"], "base": base,
                     "tree": tree, "stack": stack_of(repo, s["pr"])})
    Path(record).write_text(json.dumps({"tip": tip, "commit": commit, "prs": rows}, indent=1))
    print(commit)


def settle(repo, branch, row, landed):
    """The PR, once GitHub has had time to retarget and rebase it after its parent landed."""
    for _ in range(POLLS):
        pr = view(repo, row["pr"])
        if pr["state"] != "OPEN" or not landed.intersection(row["stack"]) or (
                pr["baseRefName"] == branch and pr["headRefOid"] != row["sha"]):
            return pr
        time.sleep(POLL)
    return pr  # not rebased: GitHub skips some, such as a branch carrying merges


def base_update(keys, row, pr, tip):
    """Push the approved head merged with `tip` as the recorded tree, with its round comment."""
    out = git("merge-tree", "--write-tree", tip, row["sha"])[1]
    resolved = git("diff", "--name-only", out.splitlines()[0], row["tree"])[1].split()
    head = git("commit-tree", row["tree"], "-p", row["sha"], "-p", tip, "-m",
               f"Merge {keys['integration_branch']} into {pr['headRefName']}")[1]
    rc, out = git("push", "-q", keys["remote"], f"{head}:refs/heads/{pr['headRefName']}")
    if rc:
        stop(5, f"#{row['pr']}: the base-update push was refused: {out}")
    k = 1 + max((int(m) for c in pr["comments"] for m in ROUND.findall(c["body"])), default=0)
    pr_state.gh(["pr", "comment", str(row["pr"]), "-R", keys["repo"], "--body",
                 f"Round {k} pushed {head[:9]}. Base update only: the tip {tip[:9]} is merged in, "
                 f"and the head's tree is the batch-gated tree `{row['tree'][:9]}`. Resolved files: "
                 + (", ".join(f"`{f}`" for f in resolved) or "none") + "."])


def land_all(keys, record, message_dir):
    repo, branch = keys["repo"], keys["integration_branch"]
    rec = json.loads(Path(record).read_text())
    message = lambda n: Path(message_dir) / f"{n}.txt"
    missing = [str(message(r["pr"])) for r in rec["prs"] if not message(r["pr"]).is_file()]
    if missing:
        stop(2, "no message file: " + ", ".join(missing))
    below, landed = git("rev-parse", rec["tip"] + "^{tree}")[1], set()
    for row in rec["prs"]:
        pr = settle(repo, branch, row, landed)
        if pr["state"] == "MERGED":
            below = row["tree"]
            landed.add(row["pr"])
            continue
        tip = land.fetch_tip(keys["remote"], branch, row["pr"])
        if git("rev-parse", tip + "^{tree}")[1] != below:
            stop(4, f"{branch} @ {tip[:12]} is not the batch's tree below #{row['pr']}: "
                    "something outside the batch landed")
        if pr["baseRefName"] != branch and pr["baseRefName"] in {
                r["branch"] for r in rec["prs"] if r["pr"] in landed}:
            pr_state.gh(["api", "-X", "PATCH", f"repos/{repo}/pulls/{row['pr']}", "-f",
                         f"base={branch}"])
        if pr["headRefOid"] == row["sha"] and land.tree_check(tip, row["sha"], expect=row["tree"]):
            base_update(keys, row, pr, tip)
        try:
            land.main([str(row["pr"]), "--message-file", str(message(row["pr"])),
                       "--expect-tree", row["tree"], "--merge-base", row["base"]])
        except SystemExit as e:
            if e.code:
                raise
        below = row["tree"]
        landed.add(row["pr"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("prs", type=int, nargs="+")
    m.add_argument("--record", required=True)
    l = sub.add_parser("land")
    l.add_argument("--record", required=True)
    l.add_argument("--message-dir", required=True)
    a = ap.parse_args(argv)
    keys, _, problems = overlay.load()
    if problems:
        stop(2, "\n".join(problems))
    if a.cmd == "merge":
        merge(keys, a.prs, a.record)
    else:
        land_all(keys, a.record, a.message_dir)


if __name__ == "__main__":
    main()
