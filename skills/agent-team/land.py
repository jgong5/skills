#!/usr/bin/env python3
"""Land one approved PR onto the integration branch, squashed.

Usage: land.py PR --message-file FILE [--expect-tree TREE [--merge-base SHA]]

Run from inside the repository. In order: refuse on any hold pr_state.py
reports; refuse a PR not based on the integration branch (land the one below
it first); compute the tree that would land on the current tip and refuse
unless it is the reviewed head's tree (or --expect-tree, a batch's gated
tree at this PR's place in it); squash through merge-async with the
checked head sha -- or, for a PR labeled `land as merge`, merge it as a
two-parent merge commit; poll until merged. Under --expect-tree an APPROVE at
another sha covers the head when both would land as that tree, the approved
sha merged from its `git merge-base` with --merge-base, or when the head's
parents are that sha and the tip and its tree is the gated one. Exit 0
merged, 2 overlay problem, 3 hold, 4 tree differs or conflicts, 5 merge
failed.
"""

import argparse
import json
import subprocess
import sys
import time

import overlay
import pr_state

TIMEOUT = 900  # seconds GitHub gets to report the merge
AS_MERGE = "land as merge"  # keeps the branch's history, such as an upstream merge


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def stop(code, msg):
    print(msg)
    sys.exit(code)


def fetch_tip(remote, branch, number):
    """The integration branch's tip, fetched with the PR's head; exits 4 if the fetch fails."""
    rc, out = git("fetch", "-q", remote, f"refs/heads/{branch}", f"refs/pull/{number}/head")
    if rc:
        stop(4, f"fetch failed: {out}")
    return git("rev-parse", "FETCH_HEAD")[1]


def tree_check(tip, sha, merge_base=None, expect=None):
    """None if merging `sha` onto `tip` yields exactly the expected tree, else why not.

    Without `merge_base` this is GitHub's own merge, the one that lands; with it,
    the merge is based on `git merge-base sha merge_base`, which GitHub never uses."""
    base = []
    if merge_base:
        rc, mb = git("merge-base", sha, merge_base)
        if rc:
            return f"{sha[:12]} and {merge_base[:12]} have no merge base"
        base = ["--merge-base", mb]
    rc, out = git("merge-tree", "--write-tree", *base, tip, sha)
    if rc:
        return f"conflicts with the tip {tip[:12]}:\n{out}"
    _, want = git("rev-parse", expect or f"{sha}^{{tree}}")
    tree = out.splitlines()[0]
    if tree != want:
        return (f"the tip {tip[:12]} has moved: the tree that would land ({tree[:12]}) "
                f"is not the {'gated' if expect else 'reviewed'} tree ({want[:12]})")
    return None


def merge(repo, number, head, title, message_file, method="squash"):
    """Merge through merge-async and poll; returns the final status object."""
    base = f"repos/{repo}/pulls/{number}/merge-async"
    out = pr_state.gh(["api", "-X", "PUT", base, "-f", f"merge_method={method}",
                       "-f", "merge_action=direct_merge", "-f", f"sha={head}",
                       "-f", f"commit_title={title}", "-F", f"commit_message=@{message_file}"],
                      check=False)
    try:
        res = json.loads(out)
    except ValueError:
        return {"status": "failed", "error": out or "no response"}
    deadline = time.monotonic() + TIMEOUT
    # A 409 (a merge already pending) carries the pending request's uuid too.
    uuid = (res.get("details") or {}).get("uuid")
    while res.get("status") not in ("merged", "failed", "enqueued"):
        if not uuid or time.monotonic() > deadline:
            return {**res, "status": "failed", "error": res.get("error") or "no uuid or timed out"}
        time.sleep(5)
        try:  # GitHub has accepted the merge: a failed poll is retried, never fatal
            res = json.loads(pr_state.gh(["api", f"{base}/{uuid}"], check=False))
        except ValueError:
            pass
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--message-file", required=True)
    ap.add_argument("--merge-base")
    ap.add_argument("--expect-tree")
    a = ap.parse_args(argv)

    keys, _, problems = overlay.load()
    if problems:
        stop(2, "\n".join(problems))
    tip = lambda: fetch_tip(keys["remote"], keys["integration_branch"], a.pr)
    tree = lambda rev: git("rev-parse", f"{rev}^{{tree}}")[1]

    def same(sha, head):
        """The gated tree, not the PR's own review, licenses a batch landing."""
        at = tip()
        # A base update: the approved head merged with the tip, its tree the gated one.
        parents = git("log", "-1", "--format=%P", head)[1].split()
        if len(parents) == 2 and parents[0].startswith(sha) and parents[1] == at:
            return tree(head) == tree(a.expect_tree)
        # A linked child GitHub rebased onto its parent's squash: new head, same content.
        return not tree_check(at, sha, a.merge_base, a.expect_tree) and not tree_check(
            at, head, expect=a.expect_tree)

    s = pr_state.state(a.pr, keys["repo"], equivalent=a.expect_tree and same)
    if s["holds"]:
        stop(3, "hold: " + "; ".join(s["holds"]))
    if s["base"] != keys["integration_branch"]:
        stop(3, f"hold: based on {s['base']}, not {keys['integration_branch']}: land the PR below first")
    why = tree_check(tip(), s["head"], expect=a.expect_tree)
    if why:
        stop(4, why)
    pr = json.loads(pr_state.gh(
        ["pr", "view", str(a.pr), "-R", keys["repo"], "--json", "title,labels"]))
    title = pr["title"]
    method = "merge" if AS_MERGE in {l["name"] for l in pr.get("labels", [])} else "squash"
    if not title.endswith(f" (#{a.pr})"):
        title += f" (#{a.pr})"  # GitHub does not add it on this endpoint
    res = merge(keys["repo"], a.pr, s["head"], title, a.message_file, method)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res.get("status") == "merged" else 5)


if __name__ == "__main__":
    main()
