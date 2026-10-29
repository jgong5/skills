#!/usr/bin/env python3
"""Who rules an item, read from its threads and assignees.

Usage: ruler.py N [--repo OWNER/NAME]

An item is an issue plus every open PR that delivers it: the PR's title names
#N, or its body does with a delivering verb, as pr_state.py reads it. N may be
a PR: the issue it delivers is the item, a PR delivering none is an item
alone, and a PR delivering several exits 2 naming them.

A request line is a comment or review whose first line opens with
`Needs owner ruling:` or `Needs ruling from @<login>:`, in any member's
thread. When the latest one names a login, that login rules (source
`request`); otherwise the issue's, or the lone PR's, single assignee does
(`assignee`), and with none or several the ruler is null (`unassigned`,
`multiple-assignees`). `Ruling on #N affects this:` is a notice, not a request.

Prints JSON: item, ruler, source, assignees, and request, the URL of the
latest request line or null.
"""

import argparse
import json
import re
import sys

from pr_state import DELIVERS, first_line, gh

REQUEST = re.compile(r"Needs (?:owner ruling|ruling from @([\w-]+)):")
TITLE_REF = re.compile(r"#(\d+)\b")
ITEM = "number,title,body,url,assignees,comments"


def delivered(pr):
    return {int(n) for n in TITLE_REF.findall(pr["title"]) + DELIVERS.findall(pr.get("body") or "")}


def entries(threads, prs, repo):
    """(time, url, first line) for every comment in `threads` and submitted review on `prs`."""
    out = [(c["createdAt"], c["url"], first_line(c["body"])) for t in threads for c in t["comments"]]
    for pr in prs:
        # Reads the first 100 reviews per PR; a longer review list needs --paginate.
        reviews = json.loads(gh(["api", f"repos/{repo or '{owner}/{repo}'}/pulls/{pr['number']}/reviews?per_page=100"]))
        out += [(r["submitted_at"], r["html_url"], first_line(r["body"])) for r in reviews if r.get("submitted_at")]
    return sorted(out)


def ruler(n, repo=None):
    r = ["-R", repo] if repo else []
    item = json.loads(gh(["issue", "view", str(n), "--json", ITEM, *r]))
    if "/pull/" in item["url"]:
        issues = sorted(delivered(item))
        if len(issues) > 1:
            print(f"#{n} delivers several issues: {', '.join(f'#{i}' for i in issues)}", file=sys.stderr)
            sys.exit(2)
        if issues:
            item = json.loads(gh(["issue", "view", str(issues[0]), "--json", ITEM, *r]))
    if "/pull/" in item["url"]:
        threads = prs = [item]
    else:
        open_prs = json.loads(gh(["pr", "list", "--state", "open", "--limit", "1000",
                                  "--json", "number,title,body,comments", *r]))
        prs = [p for p in open_prs if item["number"] in delivered(p)]
        threads = [item, *prs]
    requests = [(url, m) for _, url, line in entries(threads, prs, repo) if (m := REQUEST.match(line))]
    assignees = [a["login"] for a in item["assignees"]]
    request = requests[-1][0] if requests else None
    if requests and requests[-1][1].group(1):
        who, source = requests[-1][1].group(1), "request"
    elif len(assignees) == 1:
        who, source = assignees[0], "assignee"
    else:
        who, source = None, "multiple-assignees" if assignees else "unassigned"
    return {"item": item["number"], "ruler": who, "source": source, "assignees": assignees, "request": request}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--repo")
    a = ap.parse_args()
    print(json.dumps(ruler(a.n, a.repo), indent=1))
