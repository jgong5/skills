#!/usr/bin/env python3
"""Count a task's lines the way an estimate does: moves and deletions at a quarter weight.

Usage: line_count.py <base> [<head>]   (head defaults to HEAD; run inside the repository)

Prints one tab-separated row per changed file -- path, class (`code` or
`test`), added, moved, deleted, weighted -- then one `total` row per class,
weighted rounded up. weighted = added + (moved + deleted) / 4.

Moved lines are those `git diff --color-moved=blocks
--color-moved-ws=allow-indentation-change` paints as moved; a move counts
once, on its added side, so its deleted side counts nothing. A line edited
after its move is deleted plus added. A pure rename and a binary file count
nothing.

A file is `test` when it matches the overlay's `test_files` globs (fnmatch,
relative to the repository root, so `*` also matches `/`). With that key
unset, it is `test` when a `test`, `tests` or `__tests__` directory is in its
path or its name matches one of NAME_GLOBS.
"""

import fnmatch
import re
import subprocess
import sys

import overlay

TEST_DIRS = {"test", "tests", "__tests__"}
NAME_GLOBS = ("test_*", "*_test.*", "*.test.*", "*.spec.*")
# Colours no default theme uses, so a moved line is told by its first escape;
# git writes `#rrggbb` as the 24-bit escape beside it.
NEW_MOVED = ("#010203", "\x1b[38;2;1;2;3m")
OLD_MOVED = ("#040506", "\x1b[38;2;4;5;6m")
FILE_START = re.compile(r"(\x1b\[[0-9;]*m)*diff --git ")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def is_test(path, globs):
    if globs:
        return any(fnmatch.fnmatchcase(path, g) for g in globs)
    *dirs, name = path.split("/")
    return bool(TEST_DIRS & set(dirs)) or any(fnmatch.fnmatchcase(name, g) for g in NAME_GLOBS)


def numstat(base, head):
    """[(path, added, deleted)] in diff order; a binary file is 0, 0; a rename is its new path."""
    fields, rows = git("diff", "--no-ext-diff", "-M", "--numstat", "-z", base, head).split("\0"), []
    while len(fields) > 1:
        added, deleted, path = fields.pop(0).split("\t")
        if not path:  # a rename: source then destination follow as their own fields
            path = fields[1]
            del fields[:2]
        rows.append((path, int(added) if added != "-" else 0, int(deleted) if deleted != "-" else 0))
    return rows


def moved(base, head):
    """[(moved-to, moved-from)] per file, in the same diff order as numstat."""
    out = git("-c", f"color.diff.newMoved={NEW_MOVED[0]}", "-c", f"color.diff.oldMoved={OLD_MOVED[0]}",
              "diff", "--no-ext-diff", "-M", "--color=always", "--color-moved=blocks",
              "--color-moved-ws=allow-indentation-change", base, head)
    counts = []
    for line in out.splitlines():
        if FILE_START.match(line):
            counts.append([0, 0])
        elif line.startswith(NEW_MOVED[1]):
            counts[-1][0] += 1
        elif line.startswith(OLD_MOVED[1]):
            counts[-1][1] += 1
    return counts


def count(base, head, globs):
    """[(path, class, added, moved, deleted)] for every file changed between base and head."""
    stats, moves = numstat(base, head), moved(base, head)
    if len(stats) != len(moves):
        raise RuntimeError(f"numstat lists {len(stats)} files, the patch {len(moves)}")
    return [(path, "test" if is_test(path, globs) else "code", a - to, to, d - frm)
            for (path, a, d), (to, frm) in zip(stats, moves)]


def main(argv):
    if len(argv) not in (2, 3):
        sys.exit("usage: line_count.py <base> [<head>]")
    keys, _, problems = overlay.load()
    if problems:
        sys.exit("\n".join(problems))
    globs = [g.strip() for g in keys.get("test_files", "").split(",") if g.strip()]
    totals = {"code": [0, 0, 0], "test": [0, 0, 0]}
    for path, cls, *nums in count(argv[1], argv[2] if len(argv) == 3 else "HEAD", globs):
        a, m, d = nums
        print(f"{path}\t{cls}\t{a}\t{m}\t{d}\t{(4 * a + m + d) / 4:g}")
        totals[cls] = [t + n for t, n in zip(totals[cls], nums)]
    for cls, (a, m, d) in totals.items():
        print(f"total\t{cls}\t{a}\t{m}\t{d}\t{-(-(4 * a + m + d) // 4)}")


if __name__ == "__main__":
    main(sys.argv)
