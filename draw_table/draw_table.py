#!/usr/bin/env python3
"""Draw the datasheet and the table: read every entry in entries/, write DATASHEET.csv and TABLE.md.

This exists so the public data is exactly what the entry files say: one row
per run, one column per choice that was made, in a file anyone can load and
analyse. A pull request whose data and entries disagree fails by name.

    draw_table.py            write DATASHEET.csv and TABLE.md
    draw_table.py --check    fail if an entry is ill-formed or a drawn file is stale

A new dimension is one more line in COLUMNS. Python standard library only.
The number of desks is the suite's own.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import io
import re
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRIES = REPO_ROOT / "entries"
TABLE = REPO_ROOT / "TABLE.md"
DATASHEET = REPO_ROOT / "DATASHEET.csv"
TEMPLATE = "TEMPLATE.toml"
SUITE = REPO_ROOT / "check_bookclub" / "check_bookclub.py"
SUITE_MODULE = "the_check_suite"
COST_BASES = ("billed", "list-price", "local")
RUNS_ON = ("hosted", "local", "both")
STRANGER_RESULTS = ("pass", "fail")
NOT_RECORDED = "not recorded"
NOT_RUN = "not run"
YES, NO = "yes", "no"
LIST_SEPARATOR = "; "

Entry = dict[str, Any]


def suite_desk_count() -> int:
    """How many desks the suite checks: asked of the suite, never restated here."""
    spec = importlib.util.spec_from_file_location(SUITE_MODULE, SUITE)
    suite = importlib.util.module_from_spec(spec)
    sys.modules[SUITE_MODULE] = suite
    spec.loader.exec_module(suite)
    return suite.DESK_COUNT


DESK_COUNT = suite_desk_count()


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


def _one_of(choices: tuple[str, ...]) -> Callable[[Any], bool]:
    return lambda value: value in choices


def _matches(pattern: str) -> Callable[[Any], bool]:
    return lambda value: _text(value) and re.fullmatch(pattern, value) is not None


# Who must fill a column in.
ALWAYS = "always"  # every entry
UNDER_THE_RULES = "under the rules"  # every entry but the three reference clubs, which predate them
IF_IT_APPLIES = "if it applies"  # nobody has to


@dataclass(frozen=True)
class Column:
    """One column of the datasheet: where an entry file holds it and what it must be."""

    section: str
    name: str
    must_be: str
    holds: Callable[[Any], bool]
    needed: str = ALWAYS


# The datasheet, left to right. A new dimension is one more line here.
COLUMNS = (
    Column("build", "language", "a language", _text),
    Column("build", "frameworks", "the frameworks and libraries, in a few words", _text),
    Column("services", "event_store", "what keeps the event log", _text),
    Column("services", "read_model_store", "what keeps the read models", _text),
    Column("services", "fact_carrier", "what carries the three facts to the observer", _text),
    Column("services", "other_services", "a list, [] for none", _texts),
    Column("build", "harness", "the harness", _text),
    Column("build", "models", "a list with at least one model", lambda v: _texts(v) and len(v) > 0),
    Column("build", "provider", "who served the models", _text, UNDER_THE_RULES),
    Column("build", "addons", "a list, [] for none", _texts, UNDER_THE_RULES),
    Column("environment", "runs_on", f"one of {', '.join(RUNS_ON)}", _one_of(RUNS_ON)),
    Column("environment", "hardware", "the machine the work ran on", _text, UNDER_THE_RULES),
    Column("cost", "usd", "an amount of 0 or more", _amount),
    Column("cost", "approximate", "true or false", _flag, IF_IT_APPLIES),
    Column("cost", "basis", f"one of {', '.join(COST_BASES)}", _one_of(COST_BASES)),
    Column("cost", "tokens", "a count of 0 or more", _count, UNDER_THE_RULES),
    Column("cost", "agent_minutes", "a count of 0 or more", _count, UNDER_THE_RULES),
    Column("cost", "human_turns", "a count of 0 or more", _count, UNDER_THE_RULES),
    Column("cost", "hand_written_lines", "a count of 0 or more", _count, UNDER_THE_RULES),
    Column(
        "cost", "attempts", "a count of 1 or more", lambda v: _count(v) and v >= 1, UNDER_THE_RULES
    ),
    Column(
        "result",
        "desks",
        f"a count from 0 to {DESK_COUNT}",
        lambda v: _count(v) and v <= DESK_COUNT,
        UNDER_THE_RULES,
    ),
    Column("result", "rebuilds", "true or false", _flag, UNDER_THE_RULES),
    Column(
        "result", "stranger", f"one of {', '.join(STRANGER_RESULTS)}", _one_of(STRANGER_RESULTS)
    ),
    Column("result", "suite", "the suite version", _text, UNDER_THE_RULES),
    Column(
        "",
        "run_with",
        "the one command that starts the club and its observer",
        _text,
        UNDER_THE_RULES,
    ),
    Column("", "handle", "a name", _text),
    Column("", "repo", "an https URL", _matches(r"https://\S+")),
    Column("", "commit", "a full 40-character commit id", _matches(r"[0-9a-f]{40}")),
    Column("", "entered", "a date", lambda v: isinstance(v, datetime.date)),
    Column("", "licence", "a licence name, or none", _text),
    Column("result", "evidence", "the evidence folder in the repo", _text, UNDER_THE_RULES),
    Column("", "reference", "true or false", _flag, IF_IT_APPLIES),
    Column("result", "notes", "a few words", lambda v: isinstance(v, str), IF_IT_APPLIES),
)
# Worked out from an entry, not written in it.
COMPLETE = "complete"


def field(entry: Entry, section: str, name: str) -> Any:
    holder = entry.get(section, {}) if section else entry
    return holder.get(name) if isinstance(holder, dict) else None


def is_reference(entry: Entry) -> bool:
    return entry.get("reference") is True


def may_be_left_out(entry: Entry, column: Column) -> bool:
    return column.needed == IF_IT_APPLIES or (
        column.needed == UNDER_THE_RULES and is_reference(entry)
    )


def problems(entry: Entry) -> list[str]:
    """What is wrong with one entry; empty when it can be drawn."""
    found = []
    for column in COLUMNS:
        value = field(entry, column.section, column.name)
        if value is None and may_be_left_out(entry, column):
            continue
        if value is None or not column.holds(value):
            where = f"[{column.section}] {column.name}" if column.section else column.name
            found.append(f"{where} must be {column.must_be}")
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


def is_complete(entry: Entry) -> bool:
    every_desk = field(entry, "result", "desks") == DESK_COUNT
    rebuilt = field(entry, "result", "rebuilds") is True
    return every_desk and rebuilt and field(entry, "result", "stranger") == "pass"


def ranked(entries: list[Entry]) -> list[Entry]:
    """Complete runs first, cheapest on top; then the rest, most desks first."""

    def place(entry: Entry) -> tuple[int, float, float, str]:
        passed = field(entry, "result", "desks") or 0
        usd = entry["cost"]["usd"]
        return (0, usd, 0, entry["handle"]) if is_complete(entry) else (1, -passed, usd, "")

    return sorted(entries, key=place)


def in_order(entries: list[Entry]) -> list[Entry]:
    """The order of both drawn files: the runs under the rules, ranked, then the references."""
    references = sorted(filter(is_reference, entries), key=lambda entry: entry["cost"]["usd"])
    return ranked([entry for entry in entries if not is_reference(entry)]) + references


# ---------------------------------------------------------------------------
# The datasheet: every column, as data
# ---------------------------------------------------------------------------


def datum(value: Any) -> str:
    """One datasheet cell: plain, so a spreadsheet reads it as what it is."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return YES if value else NO
    if isinstance(value, list):
        return LIST_SEPARATOR.join(value)
    return str(value)


def datasheet(entries: list[Entry]) -> str:
    drawn = io.StringIO()
    sheet = csv.writer(drawn, lineterminator="\n")
    sheet.writerow([*(column.name for column in COLUMNS), COMPLETE])
    for entry in in_order(entries):
        cells = [datum(field(entry, column.section, column.name)) for column in COLUMNS]
        sheet.writerow([*cells, datum(is_complete(entry))])
    return drawn.getvalue()


# ---------------------------------------------------------------------------
# The table: the columns a reader compares first
# ---------------------------------------------------------------------------


def cell(value: Any) -> str:
    """One table cell: nothing in it may break the row."""
    if value is None or value == [] or value == "":
        return NOT_RECORDED
    if isinstance(value, bool):
        return YES if value else NO
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


def shown(section: str, name: str) -> Callable[[Entry], str]:
    return lambda entry: cell(field(entry, section, name))


# title -> what the cell shows
TABLE_COLUMNS: dict[str, Callable[[Entry], str]] = {
    "Language": shown("build", "language"),
    "Frameworks": shown("build", "frameworks"),
    "Event store": shown("services", "event_store"),
    "Read models": shown("services", "read_model_store"),
    "Facts travel by": shown("services", "fact_carrier"),
    "Harness": shown("build", "harness"),
    "Models": shown("build", "models"),
    "Runs on": shown("environment", "runs_on"),
    "Cost": cost,
    "Tokens": shown("cost", "tokens"),
    "Desks": desks,
    "Rebuilds": rebuilds,
    "Repository": who,
}


def rows(header: list[str], lines: list[list[str]]) -> list[str]:
    drawn = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return drawn + ["| " + " | ".join(line) + " |" for line in lines]


def main_table(entries: list[Entry]) -> list[str]:
    lines = [
        [
            str(place) if is_complete(entry) else "",
            *(show(entry) for show in TABLE_COLUMNS.values()),
        ]
        for place, entry in enumerate(entries, start=1)
    ]
    return rows(["#", *TABLE_COLUMNS], lines)


def table(entries: list[Entry]) -> str:
    under_the_rules = ranked([entry for entry in entries if not is_reference(entry)])
    references = [entry for entry in in_order(entries) if is_reference(entry)]
    page = [
        "# The table",
        "",
        "<!-- Drawn by draw_table/draw_table.py from entries/. Do not edit by hand. -->",
        "",
        "Every row is one run: an AI agent building the book club and its observer with one "
        "formula, the language, the services, the harness and the models of that row. "
        f"A run is complete when all {DESK_COUNT} desks pass, the club rebuilds its "
        "read model from the log, and the stranger test passes; "
        "complete runs are ranked by cost, cheapest first.",
        "",
        "This page shows the columns a reader compares first. Every column of every run is "
        f"in [{DATASHEET.name}]({DATASHEET.name}): load it into a spreadsheet and sort it "
        "your own way. "
        "[RULES.md](RULES.md) says what each column means.",
        "",
        "## Runs",
        "",
    ]
    if under_the_rules:
        page += main_table(under_the_rules)
    else:
        page.append(
            "No runs yet. The first row is yours: [CONTRIBUTING.md](CONTRIBUTING.md) says how."
        )
    page += [
        "",
        "## The three that started it",
        "",
        "Three clubs were built before the rules existed. Their cost is what their author "
        "remembers, and most of what the rules ask for was never recorded. They are here as "
        "the first three measurements, not as runs under the rules.",
        "",
        *main_table(references),
        "",
    ]
    return "\n".join(page)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="change nothing; fail if stale")
    parser.add_argument("--entries", type=Path, default=ENTRIES)
    parser.add_argument("--table", type=Path, default=TABLE)
    parser.add_argument("--datasheet", type=Path, default=DATASHEET)
    arguments = parser.parse_args(argv)
    entries, found = read_entries(arguments.entries)
    for problem in found:
        print(f"FAIL  {problem}", file=sys.stderr)
    if found:
        return 1
    drawn = {arguments.datasheet: datasheet(entries), arguments.table: table(entries)}
    if not arguments.check:
        for path, text in drawn.items():
            path.write_text(text, encoding="utf-8")
        return 0
    stale = [
        path
        for path, text in drawn.items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]
    for path in stale:
        print(f"FAIL  {path.name} is stale: run draw_table/draw_table.py", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
