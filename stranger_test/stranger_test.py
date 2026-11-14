#!/usr/bin/env python3
"""The stranger test: can someone who has never seen a code base read what it does from its names?

This exists so "vertical slicing and screaming architecture" is a check anyone
can run on a checkout, in any language, and not a matter of taste. It reads
file and folder names only, never file contents.

    stranger_test.py path/to/checkout
    stranger_test.py path/to/club path/to/observer    two checkouts read as one

Python standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from pathlib import Path

COMMANDS = (
    "initiate_bookclub",
    "register_member",
    "procure_book",
    "start_reading",
    "finish_reading",
    "plan_party",
    "unregister_member",
    "retire_book",
    "archive_bookclub",
)
QUERIES = (
    "get_bookclub_by_id",
    "get_member_by_id",
    "get_book_by_id",
    "get_reading_by_id",
    "get_readings_by_member",
)
# event, then the read model it is projected into
PROJECTIONS = (
    ("bookclub_initiated", "clubs"),
    ("bookclub_archived", "clubs"),
    ("member_registered", "members"),
    ("member_unregistered", "members"),
    ("book_procured", "books"),
    ("book_retired", "books"),
    ("reading_started", "readings"),
    ("reading_finished", "readings"),
)
POLICY = ("on_member_registered", "plan_party")
# what the club tells the outside world, and the word that says it leaves the club
FACTS = ("member_registered", "book_procured", "book_retired")
EMIT = "emit"
# the observer: one desk per fact it takes in, and the one question it answers
INGEST = "ingest"
SCOREBOARD = "get_scoreboard"

# Folders that sort code by technical kind instead of by what the club does.
LAYER_FOLDERS = frozenset({
    "services",
    "utils",
    "helpers",
    "repositories",
    "controllers",
    "models",
    "handlers",
    "managers",
    "dtos",
    "entities",
    "listeners",
    "projections",
    "commands",
    "events",
    "queries",
    "aggregates",
})
# Events say what happened in the club's words; these three say only that a row changed.
ROW_WORDS = frozenset({"created", "updated", "deleted"})
# Not the entrant's own code: dependencies, build output, tooling, the evidence folder.
NOT_OWN_CODE = frozenset({
    "node_modules",
    "_build",
    "deps",
    "target",
    "vendor",
    "dist",
    "build",
    "out",
    "bin",
    "obj",
    "venv",
    "__pycache__",
    "vibe",
})


def squash(name: str) -> str:
    """register_member, register-member, RegisterMember and registerMember all read the same."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def words(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [word.lower() for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def own_paths(root: Path) -> Iterator[Path]:
    """Every file and folder of the entrant's own code, relative to the checkout."""
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        hidden_or_foreign = (p.startswith(".") or p in NOT_OWN_CODE for p in relative.parts)
        if not any(hidden_or_foreign):
            yield relative


def missing_desks(names: list[str]) -> list[str]:
    """What a stranger looks for and cannot find."""
    findings = [
        f"no file or folder is named after the command {command}"
        for command in COMMANDS
        if not any(_names_command(name, command) for name in names)
    ]
    findings += [
        f"no file or folder is named after the question {query}"
        for query in QUERIES
        if not any(squash(query) in name for name in names)
    ]
    findings += [
        f"no file or folder says that {event} is projected to {table}"
        for event, table in PROJECTIONS
        if not any(_projects(name, event, table) for name in names)
    ]
    if not any(all(squash(part) in name for part in POLICY) for name in names):
        findings.append(f"no file or folder is named after the policy {'_maybe_'.join(POLICY)}")
    return findings + missing_fact_desks(names)


def missing_fact_desks(names: list[str]) -> list[str]:
    """Where each fact leaves the club, where the observer takes it in, and its question."""
    findings = [
        f"no file or folder says that the club emits {fact}"
        for fact in FACTS
        if not any(squash(EMIT + fact) in name for name in names)
    ]
    findings += [
        f"no file or folder is named after the observer's desk {INGEST}_{fact}"
        for fact in FACTS
        if not any(squash(INGEST + fact) in name for name in names)
    ]
    if not any(squash(SCOREBOARD) in name for name in names):
        findings.append(f"no file or folder is named after the question {SCOREBOARD}")
    return findings


def _names_command(name: str, command: str) -> bool:
    """unregister_member does not count as register_member."""
    return re.search(f"(?<!un){squash(command)}", name) is not None


def _projects(name: str, event: str, table: str) -> bool:
    _, found, after = name.partition(squash(event))
    return bool(found) and "to" in after and after.endswith(table)


def layer_folders(placed: list[tuple[Path, Path]]) -> list[str]:
    return [
        f"{path}/ sorts code by technical kind"
        for root, path in placed
        if (root / path).is_dir() and squash(path.name) in LAYER_FOLDERS
    ]


def row_words(paths: list[Path]) -> list[str]:
    return [
        f"{path} is named after a row change ({word})"
        for path in paths
        for word in words(path.stem)
        if word in ROW_WORDS
    ]


def findings(*roots: Path) -> list[str]:
    """Several checkouts are read as one code base: a club and an observer kept apart."""
    placed = [(root, path) for root in roots for path in own_paths(root)]
    paths = [path for _, path in placed]
    names = [squash(path.stem) for path in paths]
    return missing_desks(names) + layer_folders(placed) + row_words(paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("checkout", type=Path, nargs="+", help="the root of the code base to read")
    arguments = parser.parse_args(argv)
    not_folders = [checkout for checkout in arguments.checkout if not checkout.is_dir()]
    for checkout in not_folders:
        print(f"not a folder: {checkout}", file=sys.stderr)
    if not_folders:
        return 2
    found = findings(*arguments.checkout)
    for finding in found:
        print(f"FAIL  {finding}")
    print(f"stranger test: {'fail' if found else 'pass'} ({len(found)} findings)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
