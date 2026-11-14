"""The drawer, tested on the template and on entries made for the purpose."""

from __future__ import annotations

import csv
import io
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

import draw_table

TEMPLATE = draw_table.ENTRIES / draw_table.TEMPLATE


def template() -> draw_table.Entry:
    return tomllib.loads(TEMPLATE.read_text(encoding="utf-8"))


def entry(
    handle: str, usd: float, desks: int, stranger: str = "pass", rebuilds: bool = True
) -> draw_table.Entry:
    made = template()
    made["handle"] = handle
    made["cost"]["usd"] = usd
    made["result"]["desks"] = desks
    made["result"]["rebuilds"] = rebuilds
    made["result"]["stranger"] = stranger
    return made


def holder(made: draw_table.Entry, column: draw_table.Column) -> dict:
    return made[column.section] if column.section else made


def columns(needed: str) -> list[draw_table.Column]:
    return [column for column in draw_table.COLUMNS if column.needed == needed]


def sheet(entries: list[draw_table.Entry]) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(draw_table.datasheet(entries))))


class TheColumns(unittest.TestCase):
    def test_no_two_columns_share_a_name(self) -> None:
        names = [column.name for column in draw_table.COLUMNS] + [draw_table.COMPLETE]
        self.assertEqual(len(names), len(set(names)))

    def test_the_template_fills_in_every_column_an_entry_must_have(self) -> None:
        made = template()
        for column in columns(draw_table.ALWAYS) + columns(draw_table.UNDER_THE_RULES):
            with self.subTest(column=column.name):
                self.assertIn(column.name, holder(made, column))

    def test_the_template_names_the_number_of_desks_the_suite_checks(self) -> None:
        said = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn(f"printed: 0 to {draw_table.DESK_COUNT}\n", said)


class AnEntry(unittest.TestCase):
    def test_the_template_is_a_well_formed_entry(self) -> None:
        self.assertEqual(draw_table.problems(template()), [])

    def test_every_column_the_rules_ask_for_is_missed_by_name(self) -> None:
        for column in columns(draw_table.ALWAYS) + columns(draw_table.UNDER_THE_RULES):
            with self.subTest(column=column.name):
                broken = template()
                del holder(broken, column)[column.name]
                found = draw_table.problems(broken)
                self.assertEqual(len(found), 1)
                self.assertIn(column.name, found[0])

    def test_a_column_that_only_sometimes_applies_may_be_left_out(self) -> None:
        bare = template()
        for column in columns(draw_table.IF_IT_APPLIES):
            holder(bare, column).pop(column.name, None)
        self.assertEqual(draw_table.problems(bare), [])

    def test_values_outside_the_rules_are_refused(self) -> None:
        wrong = {
            ("cost", "basis"): "guessed",
            ("cost", "usd"): -1,
            ("cost", "attempts"): 0,
            ("cost", "approximate"): "roughly",
            ("result", "desks"): draw_table.DESK_COUNT + 1,
            ("result", "rebuilds"): "yes",
            ("result", "stranger"): "mostly",
            ("environment", "runs_on"): "somewhere",
            ("services", "other_services"): "redis",
            ("services", "event_store"): "",
            ("build", "models"): [],
            ("", "commit"): "99ab038",
            ("", "repo"): "github.com/you/club",
        }
        for (section, name), value in wrong.items():
            with self.subTest(field=name):
                broken = template()
                (broken[section] if section else broken)[name] = value
                self.assertEqual(len(draw_table.problems(broken)), 1)

    def test_a_reference_may_leave_out_what_the_rules_added_and_nothing_else(self) -> None:
        reference = template()
        reference["reference"] = True
        for column in columns(draw_table.UNDER_THE_RULES):
            del holder(reference, column)[column.name]
        self.assertEqual(draw_table.problems(reference), [])
        del reference["cost"]["usd"]
        self.assertEqual(len(draw_table.problems(reference)), 1)


class TheRanking(unittest.TestCase):
    def test_complete_runs_come_first_cheapest_on_top(self) -> None:
        every = draw_table.DESK_COUNT
        entries = [
            entry("most-desks-unfinished", 1, every - 1),
            entry("does-not-rebuild", 0.2, every, rebuilds=False),
            entry("dear", 9, every),
            entry("failed-the-stranger", 0.5, every, stranger="fail"),
            entry("cheap", 3, every),
            entry("few-desks", 0.1, 4),
        ]
        order = [made["handle"] for made in draw_table.ranked(entries)]
        self.assertEqual(
            order,
            [
                "cheap",
                "dear",
                "does-not-rebuild",
                "failed-the-stranger",
                "most-desks-unfinished",
                "few-desks",
            ],
        )

    def test_only_complete_runs_get_a_place(self) -> None:
        drawn = draw_table.main_table(
            draw_table.ranked([entry("cheap", 3, draw_table.DESK_COUNT), entry("unfinished", 1, 5)])
        )
        self.assertTrue(drawn[2].startswith("| 1 | "))
        self.assertTrue(drawn[3].startswith("|  | "))

    def test_the_same_formula_run_twice_is_two_rows(self) -> None:
        twice = [entry("again", 3, draw_table.DESK_COUNT), entry("again", 4, draw_table.DESK_COUNT)]
        self.assertEqual([row["usd"] for row in sheet(twice)], ["3", "4"])
        self.assertEqual(len(draw_table.main_table(draw_table.ranked(twice))), 4)


class TheDatasheet(unittest.TestCase):
    def test_it_has_one_column_per_dimension_and_one_row_per_run(self) -> None:
        drawn = sheet([entry("one", 3, 5), entry("two", 1, draw_table.DESK_COUNT)])
        self.assertEqual(len(drawn), 2)
        self.assertEqual(
            list(drawn[0]), [column.name for column in draw_table.COLUMNS] + [draw_table.COMPLETE]
        )

    def test_a_cell_is_plain_data(self) -> None:
        made = entry("plain", 1234.5, draw_table.DESK_COUNT)
        made["build"]["models"] = ["one", "two"]
        made["cost"]["tokens"] = 1234567
        made["result"]["notes"] = 'said "so", twice\nover'
        row = sheet([made])[0]
        self.assertEqual(row["usd"], "1234.5")
        self.assertEqual(row["tokens"], "1234567")
        self.assertEqual(row["models"], "one; two")
        self.assertEqual(row["rebuilds"], draw_table.YES)
        self.assertEqual(row["other_services"], "")
        self.assertEqual(row["entered"], "2026-12-01")
        self.assertEqual(row["notes"], 'said "so", twice\nover')
        self.assertEqual(row[draw_table.COMPLETE], draw_table.YES)

    def test_what_was_not_recorded_is_an_empty_cell(self) -> None:
        reference = entry("old", 2, 5)
        reference["reference"] = True
        del reference["cost"]["tokens"]
        row = sheet([reference])[0]
        self.assertEqual(row["tokens"], "")
        self.assertEqual(row["reference"], draw_table.YES)
        self.assertEqual(row[draw_table.COMPLETE], draw_table.NO)

    def test_the_references_come_after_the_runs_under_the_rules(self) -> None:
        reference = entry("old", 0.01, draw_table.DESK_COUNT)
        reference["reference"] = True
        drawn = sheet([reference, entry("new", 9, 3)])
        self.assertEqual([row["handle"] for row in drawn], ["new", "old"])


class TheTable(unittest.TestCase):
    def test_a_cell_cannot_break_its_row(self) -> None:
        noted = entry("noted", 3, draw_table.DESK_COUNT)
        noted["build"]["frameworks"] = "one | two\nthree"
        row = draw_table.main_table([noted])[2]
        self.assertIn("one \\| two three", row)

    def test_an_unrecorded_cell_says_so(self) -> None:
        unrecorded = entry("plain", 3, draw_table.DESK_COUNT)
        del unrecorded["cost"]["tokens"]
        self.assertIn(f"| {draw_table.NOT_RECORDED} |", draw_table.main_table([unrecorded])[2])

    def test_an_approximate_cost_is_marked(self) -> None:
        about = entry("about", 2, draw_table.DESK_COUNT)
        about["cost"]["approximate"] = True
        self.assertEqual(draw_table.cost(about), "~$2.00")
        self.assertEqual(draw_table.cost(entry("exact", 2, draw_table.DESK_COUNT)), "$2.00")

    def test_the_page_points_at_the_datasheet(self) -> None:
        self.assertIn(f"]({draw_table.DATASHEET.name})", draw_table.table([]))


class TheCheck(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.entries = Path(scratch.name) / "entries"
        self.table = Path(scratch.name) / "TABLE.md"
        self.datasheet = Path(scratch.name) / "DATASHEET.csv"
        shutil.copytree(draw_table.ENTRIES, self.entries)
        self.arguments = [
            "--entries",
            str(self.entries),
            "--table",
            str(self.table),
            "--datasheet",
            str(self.datasheet),
        ]

    def test_the_committed_files_match_the_committed_entries(self) -> None:
        self.assertEqual(draw_table.main(["--check"]), 0)

    def test_a_missing_or_stale_file_fails_the_check(self) -> None:
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)
        self.assertEqual(draw_table.main(self.arguments), 0)
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 0)
        for drawn in (self.table, self.datasheet):
            with self.subTest(drawn=drawn.name):
                kept = drawn.read_text(encoding="utf-8")
                drawn.write_text(kept + "edited by hand\n", encoding="utf-8")
                self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)
                drawn.write_text(kept, encoding="utf-8")
                self.assertEqual(draw_table.main(["--check", *self.arguments]), 0)

    def test_an_ill_formed_entry_fails_and_draws_nothing(self) -> None:
        (self.entries / "broken.toml").write_text('handle = "x"\n', encoding="utf-8")
        self.assertEqual(draw_table.main(self.arguments), 1)
        self.assertFalse(self.table.exists())
        self.assertFalse(self.datasheet.exists())

    def test_a_file_that_is_not_toml_fails(self) -> None:
        (self.entries / "broken.toml").write_text("handle = \n", encoding="utf-8")
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)

    def test_the_template_is_not_drawn(self) -> None:
        self.assertEqual(draw_table.main(self.arguments), 0)
        for drawn in (self.table, self.datasheet):
            self.assertNotIn("your-github-handle", drawn.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
