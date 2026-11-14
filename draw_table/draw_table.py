#!/usr/bin/env python3
"""Draw the table: read every entry in entries/ and write TABLE.md.

This exists so the public table is exactly what the entry files say, and a
pull request whose table and entries disagree fails by name.

    draw_table.py            write TABLE.md
    draw_table.py --check    fail if an entry is ill-formed or TABLE.md is stale

Python standard library only.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRIES = REPO_ROOT / "entries"
TABLE = REPO_ROOT / "TABLE.md"
TEMPLATE = "TEMPLATE.toml"
DESK_COUNT = 23
COST_BASES = ("billed", "list-price", "local")
STRANGER_RESULTS = ("pass", "fail")
NOT_RECORDED = "not recorded"
NOT_RUN = "not run"

Entry = dict[str, Any]


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _amount(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and value >= 0


def _texts(value: Any) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _flag(value: Any) -> bool:
    return isinstance(value, bool)


# section, field -> (what it must be, the check). Every entry needs these.
ALWAYS = {
    ("", "handle"): ("a name", _text),
    ("", "repo"): (
        "an https URL",
        lambda v: _text(v) and re.fullmatch(r"https://\S+", v) is not None,
    ),
    ("", "commit"): (
        "a full 40-character commit id",
        lambda v: _text(v) and re.fullmatch(r"[0-9a-f]{40}", v) is not None,
    ),
    ("", "entered"): ("a date", lambda v: isinstance(v, datetime.date)),
    ("", "licence"): ("a licence name, or none", _text),
    ("build", "language"): ("a language", _text),
    ("build", "stack"): ("the stack, in a few words", _text),
    ("build", "harness"): ("the harness", _text),
    ("build", "models"): ("a list with at least one model", lambda v: _texts(v) and len(v) > 0),
    ("cost", "usd"): ("an amount of 0 or more", _amount),
    ("cost", "basis"): (f"one of {', '.join(COST_BASES)}", lambda v: v in COST_BASES),
    ("result", "stranger"): (
        f"one of {', '.join(STRANGER_RESULTS)}",
        lambda v: v in STRANGER_RESULTS,
    ),
    ("result", "mesh"): ("true or false", _flag),
}
# An entry under the rules needs these too; the three reference clubs predate them.
UNDER_THE_RULES = {
    ("build", "addons"): ("a list, [] for none", _texts),
    ("cost", "tokens"): ("a count of 0 or more", _count),
    ("cost", "agent_minutes"): ("a count of 0 or more", _count),
    ("cost", "human_turns"): ("a count of 0 or more", _count),
    ("cost", "hand_written_lines"): ("a count of 0 or more", _count),
    ("cost", "attempts"): ("a count of 1 or more", lambda v: _count(v) and v >= 1),
    ("result", "desks"): (
        f"a count from 0 to {DESK_COUNT}",
        lambda v: _count(v) and v <= DESK_COUNT,
    ),
    ("result", "rebuilds"): ("true or false", _flag),
    ("result", "suite"): ("the suite version", _text),
    ("result", "evidence"): ("the evidence folder in the repo", _text),
}


def field(entry: Entry, section: str, name: str) -> Any:
    holder = entry.get(section, {}) if section else entry
    return holder.get(name) if isinstance(holder, dict) else None


def problems(entry: Entry) -> list[str]:
    """What is wrong with one entry; empty when it can be drawn."""
    is_reference = entry.get("reference") is True
    found = []
    for (section, name), (must_be, holds) in (ALWAYS | UNDER_THE_RULES).items():
        value = field(entry, section, name)
        optional = is_reference and (section, name) in UNDER_THE_RULES
        if value is None and optional:
            continue
        if value is None or not holds(value):
            where = f"[{section}] {name}" if section else name
            found.append(f"{where} must be {must_be}")
    return found


def read_entries(folder: Path) -> tuple[list[Entry], list[str]]:
    entries, found = [], []
    for path in sorted(folder.glob("*.toml")):
        if path.name == TEMPLATE:
            continue
        try:
            entry = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            found.append(f"{path.name}: not valid TOML: {error}")
            continue
        found += [f"{path.name}: {problem}" for problem in problems(entry)]
        entries.append(entry)
    return entries, found


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def cell(value: Any) -> str:
    """One table cell: nothing in it may break the row."""
    if value is None or value == [] or value == "":
        return NOT_RECORDED
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        value = ", ".join(value)
    if isinstance(value, int):
        return f"{value:,}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def who(entry: Entry) -> str:
    name = entry["repo"].rstrip("/").rsplit("/", 1)[-1]
    return f"[{cell(entry['handle'])}/{cell(name)}]({entry['repo']})"


def cost(entry: Entry) -> str:
    about = "~" if field(entry, "cost", "approximate") is True else ""
    return f"{about}${entry['cost']['usd']:,.2f}"


def desks(entry: Entry) -> str:
    passed = field(entry, "result", "desks")
    return NOT_RUN if passed is None else f"{passed} of {DESK_COUNT}"


def rebuilds(entry: Entry) -> str:
    rebuilt = field(entry, "result", "rebuilds")
    return NOT_RUN if rebuilt is None else cell(rebuilt)


def addons(entry: Entry) -> str:
    listed = field(entry, "build", "addons")
    return "none" if listed == [] else cell(listed)


def is_complete(entry: Entry) -> bool:
    every_desk = field(entry, "result", "desks") == DESK_COUNT
    rebuilt = field(entry, "result", "rebuilds") is True
    return every_desk and rebuilt and field(entry, "result", "stranger") == "pass"


def ranked(entries: list[Entry]) -> list[Entry]:
    """Complete entries first, cheapest on top; then the rest, most desks first."""

    def place(entry: Entry) -> tuple[int, float, float, str]:
        passed = field(entry, "result", "desks") or 0
        usd = entry["cost"]["usd"]
        return (0, usd, 0, entry["handle"]) if is_complete(entry) else (1, -passed, usd, "")

    return sorted(entries, key=place)


def rows(header: list[str], lines: list[list[str]]) -> list[str]:
    drawn = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return drawn + ["| " + " | ".join(line) + " |" for line in lines]


def main_table(entries: list[Entry]) -> list[str]:
    header = [
        "#",
        "Who",
        "Language",
        "Stack",
        "Harness",
        "Models",
        "Add-ons",
        "Cost",
        "Desks",
        "Rebuilds",
    ]
    lines = [
        [
            str(place) if is_complete(entry) else "",
            who(entry),
            cell(entry["build"]["language"]),
            cell(entry["build"]["stack"]),
            cell(entry["build"]["harness"]),
            cell(entry["build"]["models"]),
            addons(entry),
            cost(entry),
            desks(entry),
            rebuilds(entry),
        ]
        for place, entry in enumerate(entries, start=1)
    ]
    return rows(header, lines)


def fine_print(entries: list[Entry]) -> list[str]:
    header = [
        "Who",
        "Cost basis",
        "Tokens",
        "Agent minutes",
        "Human turns",
        "Hand-written lines",
        "Attempts",
        "Suite",
        "Stranger test",
        "Mesh",
        "Licence",
        "Commit",
        "Entered",
        "Notes",
    ]
    lines = [
        [
            who(entry),
            cell(entry["cost"]["basis"]),
            *(
                cell(field(entry, "cost", name))
                for name in (
                    "tokens",
                    "agent_minutes",
                    "human_turns",
                    "hand_written_lines",
                    "attempts",
                )
            ),
            cell(field(entry, "result", "suite")),
            cell(entry["result"]["stranger"]),
            cell(entry["result"]["mesh"]),
            cell(entry["licence"]),
            f"[`{entry['commit'][:7]}`]({entry['repo'].rstrip('/')}/tree/{entry['commit']})",
            cell(entry["entered"]),
            cell(field(entry, "result", "notes")) if field(entry, "result", "notes") else "",
        ]
        for entry in entries
    ]
    return rows(header, lines)


def draw(entries: list[Entry]) -> str:
    under_the_rules = ranked([entry for entry in entries if entry.get("reference") is not True])
    references = sorted(
        (entry for entry in entries if entry.get("reference") is True),
        key=lambda entry: entry["cost"]["usd"],
    )
    page = [
        "# The table",
        "",
        "<!-- Drawn by draw_table/draw_table.py from entries/. Do not edit by hand. -->",
        "",
        "Every row is one book club, built by an AI agent, in a public repository. "
        f"A row is complete when all {DESK_COUNT} desks pass, the club rebuilds its read model "
        "from the log, and the stranger test passes; "
        "complete rows are ranked by cost, cheapest first. "
        "[RULES.md](RULES.md) says what each number means.",
        "",
        "## Entries",
        "",
    ]
    if under_the_rules:
        page += main_table(under_the_rules)
        page += ["", "### The fine print", "", *fine_print(under_the_rules)]
    else:
        page.append(
            "No entries yet. The first row is yours: [CONTRIBUTING.md](CONTRIBUTING.md) says how."
        )
    page += [
        "",
        "## The three that started it",
        "",
        "Three clubs were built before the rules existed. Their cost is what their author "
        "remembers, and the numbers the rules ask for were never recorded. They are here as "
        "the mark to beat, not as entries.",
        "",
        *main_table(references),
        "",
        "### The fine print",
        "",
        *fine_print(references),
        "",
    ]
    return "\n".join(page)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="change nothing; fail if stale")
    parser.add_argument("--entries", type=Path, default=ENTRIES)
    parser.add_argument("--table", type=Path, default=TABLE)
    arguments = parser.parse_args(argv)
    entries, found = read_entries(arguments.entries)
    for problem in found:
        print(f"FAIL  {problem}", file=sys.stderr)
    if found:
        return 1
    drawn = draw(entries)
    if not arguments.check:
        arguments.table.write_text(drawn, encoding="utf-8")
        return 0
    on_disk = arguments.table.read_text(encoding="utf-8") if arguments.table.exists() else ""
    if on_disk != drawn:
        print(
            f"FAIL  {arguments.table.name} is stale: run draw_table/draw_table.py", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
