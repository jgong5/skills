#!/usr/bin/env python3
"""Verify an implementation study's claim ledger and the repository boundary.

    <skill-dir>/check_evidence.py snapshot       --repo-root ROOT --output-dir OUT --snapshot FILE [--cited-file PATH ...]
    <skill-dir>/check_evidence.py extend-snapshot --repo-root ROOT --output-dir OUT --snapshot FILE [--cited-file PATH ...]
    <skill-dir>/check_evidence.py verify STUDY NOTES --repo-root ROOT --output-dir OUT [--snapshot FILE]

`verify` is the Phase 5 gate. It reads the ledger out of `<stem>_study.notes.md`
and checks, mechanically:

  * every entry parses as `- [ID] <claim>. <class>: <source>` with one of the
    three evidence classes, no duplicate IDs, and a backticked anchor on every
    `path:line` citation
  * every file citation resolves inside the repository and its anchor still
    sits on the cited line -- a moved anchor is reported with its new line
    number rather than silently accepted
  * every derivation names ledger IDs that exist, shows its reasoning after
    `--`, and takes part in no cycle
  * every measurement points at a script and an output that both exist in one
    experiments directory next to an `ENV.md` and an approved `PLAN.md` line
  * every `[ID]` reference in the prose exists in the ledger
  * nothing outside the output directory changed, via `git status` in a work
    tree or via the `<stem>_study.integrity.json` snapshot otherwise

The point of the ledger is that a claim without evidence cannot reach the
prose by accident: the checker cannot tell a true sentence from a false one,
but it can tell a sourced one from an unsourced one, and it refuses to let a
citation rot into pointing at the wrong line.

Exit 0 means clean -- prints "clean: N ledger entries verified". Exit 1 means
read the PROBLEM: lines on stderr.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Machine-readable contract with writing.md's ledger grammar. Change both ends
# together: the prose documents this syntax to the author, this module is what
# actually enforces it.
ENTRY_RE = re.compile(
    r"^- \[([A-Z][A-Z0-9_-]*)\] (.+?)\. (cite|derive|measure): (.+)$"
)
FILE_CITE_RE = re.compile(
    r"(?P<path>[^\s,:`]+):(?P<start>\d+)(?:-(?P<end>\d+))?\s+`(?P<anchor>[^`]+)`"
)
REFERENCE_RE = re.compile(r"\b([A-Z][A-Z0-9_-]*\d+)\b")
PROSE_REF_RE = re.compile(r"\[([A-Z][A-Z0-9_-]*)\]")
MEASURE_RE = re.compile(r"^(?P<script>\S+)\s+->\s+(?P<output>\S+)$")
PLAN_RE = re.compile(r"^- \[x\] \[(?P<id>[A-Z][A-Z0-9_-]*)\] (?P<script>\S+) -- .+$")

# A line that opens like a ledger entry must parse as one. Anything else in the
# notes file (headings, prose, PLAN.md-style `- [x] ...` lines) is not a ledger
# entry and is ignored rather than rejected.
ENTRY_PREFIX_RE = re.compile(r"^- \[[A-Z][A-Z0-9_-]*\]")
# Same shape as FILE_CITE_RE's path:line prefix, with no anchor. Used only to
# catch a file citation that forgot its backticked anchor.
BARE_FILE_CITE_RE = re.compile(r"[^\s,:`]+:\d+(?:-\d+)?")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
URL_RE = re.compile(r"\bhttps?://\S+")
FENCE_RE = re.compile(r"^(```|~~~)")

SNAPSHOT_VERSION = 1
HASH_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    claim: str
    kind: str
    source: str
    line: int


class EvidenceFormatError(ValueError):
    pass


class PathEscapeError(ValueError):
    """A path in the ledger points outside the root it must stay under."""


def _blank(match: re.Match) -> str:
    return " " * len(match.group(0))


def _resolve_under(base: Path, relative: str) -> Path:
    """Join `relative` onto `base`, refusing absolute paths and `..` escapes.

    Deliberately lexical: `Path.resolve()` would also follow symlinks, so a
    repository that legitimately lives behind one would look like an escape.
    What matters here is that the ledger cannot name `../../etc/passwd`.
    """
    candidate = Path(relative)
    if candidate.is_absolute():
        raise PathEscapeError(f"absolute path {relative}")
    normalized = os.path.normpath(str(candidate))
    if normalized == ".." or normalized.startswith(".." + os.sep):
        raise PathEscapeError(f"path escapes the root: {relative}")
    return base / normalized


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _join_continuations(text: str) -> list[tuple[int, str]]:
    """Fold indented continuation lines into the entry they belong to.

    A long claim wraps in the notes file; the wrapped remainder is indented.
    Returns (line number of the entry's first line, joined text) pairs.
    """
    joined: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        if raw[:1] in (" ", "\t") and joined:
            start, previous = joined[-1]
            joined[-1] = (start, previous + " " + raw.strip())
        else:
            joined.append((number, raw.rstrip()))
    return joined


def _check_anchored(entry_id: str, source: str, number: int) -> None:
    """Reject a `path:line` citation that carries no backticked anchor.

    An anchor is what makes a citation checkable: without it a line number is
    just a number, and it rots the moment anyone inserts a line above it. URLs,
    commit SHAs, and paper references are external citations with no line to
    anchor to, so they are scrubbed before the check rather than demanded of.
    """
    scrubbed = FILE_CITE_RE.sub(_blank, source)
    scrubbed = INLINE_CODE_RE.sub(_blank, scrubbed)
    scrubbed = URL_RE.sub(_blank, scrubbed)
    bare = BARE_FILE_CITE_RE.search(scrubbed)
    if bare:
        raise EvidenceFormatError(
            f"line {number}: {entry_id} cites {bare.group(0)} with no "
            "backticked anchor"
        )


def parse_ledger(text: str) -> dict[str, LedgerEntry]:
    """Parse the claim ledger out of `<stem>_study.notes.md`.

    Raises EvidenceFormatError for a malformed entry, an unknown evidence
    class, a duplicate ID, or a file citation missing its anchor.
    """
    entries: dict[str, LedgerEntry] = {}
    for number, line in _join_continuations(text):
        if not ENTRY_PREFIX_RE.match(line):
            continue
        match = ENTRY_RE.match(line)
        if not match:
            raise EvidenceFormatError(
                f"line {number}: not a ledger entry -- expected "
                f"'- [ID] <claim>. <cite|derive|measure>: <source>': {line}"
            )
        entry_id, claim, kind, source = match.groups()
        if entry_id in entries:
            raise EvidenceFormatError(
                f"line {number}: duplicate {entry_id} (first seen on line "
                f"{entries[entry_id].line})"
            )
        if kind == "cite":
            _check_anchored(entry_id, source, number)
        entries[entry_id] = LedgerEntry(
            id=entry_id, claim=claim, kind=kind, source=source, line=number
        )
    return entries


def check_citations(entries: dict[str, LedgerEntry], repo_root: Path) -> list[str]:
    """Check that every `path:line[-line]` citation still says what it cited.

    Only file citations are checkable here. A commit SHA, a URL, or a paper
    reference stays a human-checked external citation -- the skill's rule is
    that those are cited, not that this script can verify them.
    """
    repo_root = Path(repo_root)
    problems: list[str] = []
    for entry in entries.values():
        if entry.kind != "cite":
            continue
        for match in FILE_CITE_RE.finditer(entry.source):
            problems.extend(_check_one_citation(entry, match, repo_root))
    return problems


def _check_one_citation(
    entry: LedgerEntry, match: re.Match, repo_root: Path
) -> list[str]:
    rel = match.group("path")
    start = int(match.group("start"))
    end = int(match.group("end")) if match.group("end") else start
    anchor = _normalize_ws(match.group("anchor"))
    try:
        target = _resolve_under(repo_root, rel)
    except PathEscapeError as exc:
        return [f"{entry.id}: {exc}"]
    if not target.is_file():
        return [f"{entry.id}: cited file {rel} does not exist"]
    lines = target.read_text(errors="replace").splitlines()
    if start < 1 or end < start or end > len(lines):
        return [
            f"{entry.id}: cited line {start}"
            + (f"-{end}" if end != start else "")
            + f" is outside {rel}, which has {len(lines)} line(s)"
        ]
    cited = _normalize_ws(" ".join(lines[start - 1:end]))
    if anchor in cited:
        return []
    elsewhere = [
        n for n, line in enumerate(lines, start=1) if anchor in _normalize_ws(line)
    ]
    if len(elsewhere) == 1:
        return [
            f"{entry.id}: anchor moved to line {elsewhere[0]} in {rel} "
            f"(cited line {start})"
        ]
    if elsewhere:
        shown = ", ".join(str(n) for n in elsewhere[:5])
        return [
            f"{entry.id}: anchor does not match {rel}:{start}; it appears on "
            f"lines {shown}"
        ]
    return [f"{entry.id}: anchor {match.group('anchor')!r} does not appear in {rel}"]


def check_derivations(entries: dict[str, LedgerEntry]) -> list[str]:
    """Check that every derivation names real ledger IDs, shows its work, and
    does not stand in a cycle.

    A derivation reads `derive: C1, C3 -- <reasoning>`. The reasoning after
    `--` is mandatory: `derive: C1` alone asserts that a conclusion follows
    from a premise without saying how, which is the exact move the ledger
    exists to prevent. A cycle is the same failure wearing a longer path --
    every claim is supported and nothing is grounded.
    """
    problems: list[str] = []
    edges: dict[str, list[str]] = {}
    for entry in entries.values():
        if entry.kind != "derive":
            continue
        head, separator, reasoning = entry.source.partition("--")
        if not separator or not reasoning.strip():
            problems.append(
                f"{entry.id}: derivation has no reasoning after '--'"
            )
        references = REFERENCE_RE.findall(head)
        for reference in references:
            if reference not in entries:
                problems.append(f"{entry.id}: unknown ledger id {reference}")
        edges[entry.id] = [r for r in references if r in entries]

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = stack[stack.index(node):] + [node]
            problems.append(f"{node}: derivation cycle {' -> '.join(cycle)}")
            return
        visiting.add(node)
        stack.append(node)
        for reference in edges.get(node, ()):
            visit(reference)
        stack.pop()
        visiting.discard(node)
        visited.add(node)

    for entry_id in edges:
        visit(entry_id)
    return problems


def check_measurements(entries: dict[str, LedgerEntry], output_dir: Path) -> list[str]:
    """Check that every measurement points at real, approved, reproducible
    artifacts inside one experiments directory.

    A measurement claim is only as good as the run behind it, so the checker
    demands the whole run: the script, its captured output, the `ENV.md` that
    says what machine produced it, and the `PLAN.md` line where the user
    approved this exact script for this exact ledger ID before it ran. An
    unapproved measurement is not a weak measurement, it is code this skill
    had no permission to execute.
    """
    output_dir = Path(output_dir)
    problems: list[str] = []
    for entry in entries.values():
        if entry.kind != "measure":
            continue
        problems.extend(_check_one_measurement(entry, output_dir))
    return problems


def _check_one_measurement(entry: LedgerEntry, output_dir: Path) -> list[str]:
    match = MEASURE_RE.match(entry.source.strip())
    if not match:
        return [
            f"{entry.id}: measurement source must be '<script> -> <output>', "
            f"got {entry.source!r}"
        ]
    try:
        script = _resolve_under(output_dir, match.group("script"))
        output = _resolve_under(output_dir, match.group("output"))
    except PathEscapeError as exc:
        return [f"{entry.id}: {exc}"]
    for label, path, rel in (
        ("script", script, match.group("script")),
        ("output", output, match.group("output")),
    ):
        if not path.is_file():
            return [f"{entry.id}: measurement {label} {rel} does not exist"]
    if script.parent != output.parent:
        return [
            f"{entry.id}: script and output must live in the same experiments "
            f"directory ({match.group('script')} vs {match.group('output')})"
        ]
    experiments = script.parent
    for required in ("ENV.md", "PLAN.md"):
        if not (experiments / required).is_file():
            return [
                f"{entry.id}: {experiments.name}/ has no {required}"
            ]
    plan_text = (experiments / "PLAN.md").read_text(errors="replace")
    for line in plan_text.splitlines():
        plan = PLAN_RE.match(line.rstrip())
        if plan and plan.group("id") == entry.id and plan.group("script") == script.name:
            return []
    return [
        f"{entry.id}: no approved PLAN.md line for {script.name} -- expected "
        f"'- [x] [{entry.id}] {script.name} -- <description>' in "
        f"{experiments.name}/PLAN.md"
    ]


def check_prose_coverage(prose: str, entries: dict[str, LedgerEntry]) -> list[str]:
    """Report every `[ID]` the prose cites that the ledger does not define.

    The reverse -- a ledger entry the prose never cites -- is allowed on
    purpose: analysis turns up evidence that does not make the final cut, and
    deleting it to satisfy a checker would throw away the audit trail. Fenced
    code is skipped because `writing.md` documents this very syntax in fences.
    """
    unknown: list[str] = []
    seen: set[str] = set()
    in_fence = False
    for line in prose.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in PROSE_REF_RE.finditer(line):
            reference = match.group(1)
            if reference in entries or reference in seen:
                continue
            seen.add(reference)
            unknown.append(f"prose references unknown ledger id {reference}")
    return unknown


def is_git_work_tree(repo_root: Path) -> bool:
    """True when `repo_root` is inside a git work tree."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _unquote_git_path(path: str) -> str:
    """Undo `git status`'s C-style quoting of paths with unusual bytes."""
    if not path.startswith('"'):
        return path
    try:
        return json.loads(path)
    except ValueError:
        return path.strip('"')


def _is_under(path: Path, directory: Path) -> bool:
    resolved = os.path.realpath(str(path))
    base = os.path.realpath(str(directory))
    return resolved == base or resolved.startswith(base.rstrip(os.sep) + os.sep)


def check_git_integrity(repo_root: Path, output_dir: Path) -> list[str]:
    """Check that the working tree grew skill outputs and nothing else.

    The study is a read-only act: the repository under study must come out of
    it byte for byte as it went in. In a work tree that reduces to one rule --
    every `git status` entry must be untracked (`??`) and must live inside the
    output directory. A tracked modification means the skill (or something it
    ran) edited the subject; an untracked file elsewhere means it littered.
    """
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    if not is_git_work_tree(repo_root):
        return [f"{repo_root} is not a git work tree"]
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1",
         "--untracked-files=all"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return [f"git status failed: {result.stderr.strip()}"]
    problems: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status, rest = line[:2], line[3:]
        # A rename reads "R  old -> new"; the new path is the one on disk.
        if " -> " in rest:
            rest = rest.split(" -> ")[-1]
        rel = _unquote_git_path(rest)
        if status != "??":
            problems.append(f"tracked change: {status.strip() or status} {rel}")
            continue
        if not _is_under(repo_root / rel, output_dir):
            problems.append(f"untracked file outside output directory: {rel}")
    return problems


def _walk_metadata(repo_root: Path, output_dir: Path) -> dict[str, dict[str, int]]:
    """Size and mtime of every regular file under `repo_root`, output aside.

    Symlinks -- to files or to directories -- are skipped rather than
    followed, so a link pointing out of the repository cannot drag unrelated
    files into the baseline or make a change outside it look like one inside.
    """
    repo_root = Path(repo_root)
    files: dict[str, dict[str, int]] = {}
    for dirpath, dirnames, filenames in os.walk(repo_root, followlinks=False):
        here = Path(dirpath)
        dirnames[:] = sorted(
            name for name in dirnames
            if not (here / name).is_symlink()
            and not _is_under(here / name, output_dir)
        )
        if _is_under(here, output_dir):
            continue
        for name in sorted(filenames):
            path = here / name
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(repo_root).as_posix()
            stat = path.stat()
            files[rel] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_cited(
    repo_root: Path, output_dir: Path, cited_paths: list[Path]
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for cited in cited_paths:
        target = _resolve_under(Path(repo_root), str(cited))
        rel = target.relative_to(repo_root).as_posix()
        if _is_under(target, output_dir):
            raise ValueError(
                f"cited path {rel} is inside the output directory, which the "
                "snapshot deliberately excludes"
            )
        if not target.is_file():
            raise ValueError(f"cited path {rel} is not a file")
        hashes[rel] = _sha256(target)
    return hashes


def _write_json_atomically(snapshot_path: Path, data: dict) -> None:
    """Serialize deterministically through a sibling temp file and replace.

    Deterministic (sorted keys, one trailing newline) so re-running `snapshot`
    on an unchanged tree produces a byte-identical file and a diff means
    something. Atomic so an interrupted write cannot leave behind a truncated
    baseline that would then "verify" against anything.
    """
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    snapshot_path = Path(snapshot_path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=str(snapshot_path.parent), prefix=snapshot_path.name, suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(payload)
        Path(temporary).replace(snapshot_path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_integrity_snapshot(
    repo_root: Path, output_dir: Path, snapshot_path: Path, cited_paths: list[Path]
) -> None:
    """Record the pre-study state of a repository with no version control.

    Metadata for every file outside the output directory catches additions,
    deletions, and edits cheaply; SHA-256 for the cited files catches the one
    case metadata can miss -- a same-size edit restored to its old mtime.
    """
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    data = {
        "version": SNAPSHOT_VERSION,
        "root": ".",
        "excluded_output": _relative_output(repo_root, output_dir),
        "files": _walk_metadata(repo_root, output_dir),
        "hashes": _hash_cited(repo_root, output_dir, cited_paths),
    }
    _write_json_atomically(Path(snapshot_path), data)


def _relative_output(repo_root: Path, output_dir: Path) -> str:
    try:
        return Path(os.path.relpath(str(output_dir), str(repo_root))).as_posix()
    except ValueError:
        return str(output_dir)


def check_snapshot_integrity(
    repo_root: Path, output_dir: Path, snapshot_path: Path
) -> list[str]:
    """Compare the repository against its snapshot baseline."""
    repo_root = Path(repo_root)
    output_dir = Path(output_dir)
    snapshot_path = Path(snapshot_path)
    if not snapshot_path.is_file():
        return [f"integrity snapshot {snapshot_path} does not exist"]
    try:
        data = json.loads(snapshot_path.read_text())
    except ValueError as exc:
        return [f"integrity snapshot {snapshot_path} is not valid JSON: {exc}"]
    if data.get("version") != SNAPSHOT_VERSION:
        return [
            f"integrity snapshot version {data.get('version')!r} is not "
            f"{SNAPSHOT_VERSION}"
        ]
    recorded = data.get("files", {})
    current = _walk_metadata(repo_root, output_dir)
    problems: list[str] = []
    for rel in sorted(set(current) - set(recorded)):
        problems.append(f"added file outside output directory: {rel}")
    for rel in sorted(set(recorded) - set(current)):
        problems.append(f"deleted file: {rel}")
    for rel in sorted(set(recorded) & set(current)):
        was, now = recorded[rel], current[rel]
        if was.get("size") != now["size"]:
            problems.append(
                f"{rel}: size changed {was.get('size')} -> {now['size']}"
            )
        elif was.get("mtime_ns") != now["mtime_ns"]:
            problems.append(f"{rel}: mtime changed")
    for rel in sorted(data.get("hashes", {})):
        target = repo_root / rel
        if not target.is_file():
            continue  # already reported as a deletion
        if _sha256(target) != data["hashes"][rel]:
            problems.append(f"{rel}: hash changed")
    return problems


def extend_integrity_snapshot(
    repo_root: Path, output_dir: Path, snapshot_path: Path, cited_paths: list[Path]
) -> list[str]:
    """Add hashes for newly cited files, but only to an intact baseline.

    Phase 2 cites files Phase 1 did not know about, so the baseline has to
    grow. Verifying first is what keeps that from becoming a laundry: if
    something already changed, re-recording it would bless the change and
    erase the evidence, so the extension is refused and the problems are
    returned instead.
    """
    problems = check_snapshot_integrity(repo_root, output_dir, snapshot_path)
    if problems:
        return problems
    snapshot_path = Path(snapshot_path)
    data = json.loads(snapshot_path.read_text())
    data.setdefault("hashes", {}).update(
        _hash_cited(Path(repo_root), Path(output_dir), cited_paths)
    )
    _write_json_atomically(snapshot_path, data)
    return []


def _report(problems: list[str]) -> int:
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    return 1


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, metavar="ROOT")
    parser.add_argument("--output-dir", required=True, metavar="OUT")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_evidence.py",
        description="Verify an implementation study's ledger and repository "
                    "boundary.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("snapshot", "record the pre-study state of a non-git repository"),
        ("extend-snapshot", "hash newly cited files against an intact baseline"),
    ):
        sub = subcommands.add_parser(name, help=help_text)
        _add_common(sub)
        sub.add_argument("--snapshot", required=True, metavar="FILE")
        sub.add_argument("--cited-file", action="extend", nargs="+", default=[],
                         metavar="PATH",
                         help="repository-relative path to hash (repeatable)")

    verify = subcommands.add_parser("verify", help="check the ledger and the "
                                                   "repository boundary")
    verify.add_argument("study", metavar="STUDY")
    verify.add_argument("notes", metavar="NOTES")
    _add_common(verify)
    verify.add_argument("--snapshot", metavar="FILE")
    return parser


def _verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    try:
        study_text = Path(args.study).read_text()
        notes_text = Path(args.notes).read_text()
    except OSError as exc:
        return _report([str(exc)])
    try:
        entries = parse_ledger(notes_text)
    except EvidenceFormatError as exc:
        return _report([str(exc)])

    problems: list[str] = []
    problems += check_citations(entries, repo_root)
    problems += check_derivations(entries)
    problems += check_measurements(entries, output_dir)
    problems += check_prose_coverage(study_text, entries)

    in_git = is_git_work_tree(repo_root)
    if in_git:
        problems += check_git_integrity(repo_root, output_dir)
    if args.snapshot:
        problems += check_snapshot_integrity(
            repo_root, output_dir, Path(args.snapshot)
        )
    elif not in_git:
        # Silence here would be the worst outcome: a study that never proved
        # it left the repository alone would still print "clean".
        problems.append(
            f"{repo_root} is not a git work tree and no --snapshot was "
            "supplied, so the no-modification boundary is unverified"
        )

    if problems:
        return _report(problems)
    print(f"clean: {len(entries)} ledger entries verified")
    return 0


def main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "verify":
        return _verify(args)

    repo_root = Path(args.repo_root)
    output_dir = Path(args.output_dir)
    snapshot = Path(args.snapshot)
    cited = [Path(p) for p in args.cited_file]
    try:
        if args.command == "snapshot":
            write_integrity_snapshot(repo_root, output_dir, snapshot, cited)
        else:
            problems = extend_integrity_snapshot(
                repo_root, output_dir, snapshot, cited
            )
            if problems:
                return _report(problems)
    except (ValueError, OSError) as exc:
        return _report([str(exc)])
    data = json.loads(snapshot.read_text())
    verb = "wrote" if args.command == "snapshot" else "extended"
    print(f"{verb} {snapshot}: {len(data['files'])} files tracked, "
          f"{len(data['hashes'])} hashed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
