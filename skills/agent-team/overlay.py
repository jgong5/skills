#!/usr/bin/env python3
"""Read a project's agent-team overlay.

Usage: overlay.py   (reads .claude/agent-team.md under the work tree's root)

Prints the resolved keys as JSON and exits 0, or prints every problem and
exits 1. The keys and their meaning are documented in overlay.md.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_PATH = ".claude/agent-team.md"
REQUIRED = ("repo", "integration_branch", "gate_task", "design_entry")
DEFAULTS = {"publish_language": "English", "max_tasks": "5", "split_loc": "1000"}
OPTIONAL = ("remote", "never_touch", "gate_wave", "new_tests_dir", "import_check",
            "worktree_root", "task_label", "prose_tests")
INTEGER = ("max_tasks", "split_loc")
KEYS = REQUIRED + OPTIONAL + tuple(DEFAULTS)


def parse(text):
    """Split an overlay into its flat `key: value` frontmatter and its body."""
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text, ["no frontmatter: the file must open with a --- block"]
    keys, problems = {}, []
    for n, line in enumerate(m.group(1).splitlines(), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not value:
            problems.append(f"line {n}: not `key: value`: {line!r}")
        elif key not in KEYS:
            problems.append(f"line {n}: unknown key {key!r}")
        else:
            keys[key] = value
    return keys, m.group(2), problems


def remotes_for(repo, remote_v):
    """Names of the remotes whose URL points at `repo` (OWNER/NAME), from `git remote -v`."""
    names = []
    for line in remote_v.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        url = parts[1].lower().removesuffix("/").removesuffix(".git")
        if re.search(r"github\.com[:/]" + re.escape(repo.lower()) + "$", url) and parts[0] not in names:
            names.append(parts[0])
    return names


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def load(path=DEFAULT_PATH):
    """Resolved keys, the body, and a list of problems (empty when usable)."""
    if path == DEFAULT_PATH:
        path = Path(git("rev-parse", "--show-toplevel")) / DEFAULT_PATH
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        return {}, "", [f"cannot read {path}: {e.strerror}"]
    keys, body, problems = parse(text)
    problems += [f"missing required key {k!r}" for k in REQUIRED if k not in keys]
    for k, v in DEFAULTS.items():
        keys.setdefault(k, v)
    for k in INTEGER:
        if not keys[k].isdigit() or int(keys[k]) < 1:
            problems.append(f"{k} must be a positive integer, got {keys[k]!r}")
    if "repo" in keys and "remote" not in keys:
        found = remotes_for(keys["repo"], git("remote", "-v"))
        if len(found) == 1:
            keys["remote"] = found[0]
        else:
            problems.append(f"{len(found)} remotes point at {keys['repo']}: {found}; "
                            "name one with the `remote` key")
    if "worktree_root" not in keys:
        main = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")).parent
        keys["worktree_root"] = str(main.parent / f"{main.name}-worktrees")
    return keys, body, problems


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit("usage: overlay.py (takes no arguments)")
    keys, body, problems = load()
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print(json.dumps(keys, indent=1))
