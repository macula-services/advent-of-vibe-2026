"""The table drawer, tested on the template and on entries made for the purpose."""

from __future__ import annotations

import copy
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


class AnEntry(unittest.TestCase):
    def test_the_template_is_a_well_formed_entry(self) -> None:
        self.assertEqual(draw_table.problems(template()), [])

    def test_every_field_the_rules_ask_for_is_missed_by_name(self) -> None:
        for section, name in draw_table.ALWAYS | draw_table.UNDER_THE_RULES:
            with self.subTest(field=name):
                broken = template()
                del (broken[section] if section else broken)[name]
                found = draw_table.problems(broken)
                self.assertEqual(len(found), 1)
                self.assertIn(name, found[0])

    def test_values_outside_the_rules_are_refused(self) -> None:
        wrong = {
            ("cost", "basis"): "guessed",
            ("cost", "usd"): -1,
            ("cost", "attempts"): 0,
            ("result", "desks"): draw_table.DESK_COUNT + 1,
            ("result", "rebuilds"): "yes",
            ("result", "stranger"): "mostly",
            ("result", "mesh"): "yes",
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
        for section, name in draw_table.UNDER_THE_RULES:
            del (reference[section] if section else reference)[name]
        self.assertEqual(draw_table.problems(reference), [])
        del reference["cost"]["usd"]
        self.assertEqual(len(draw_table.problems(reference)), 1)


class TheDeskCount(unittest.TestCase):
    def test_the_template_names_the_number_of_desks_the_suite_checks(self) -> None:
        said = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn(f"printed: 0 to {draw_table.DESK_COUNT}\n", said)


class TheRanking(unittest.TestCase):
    def test_complete_entries_come_first_cheapest_on_top(self) -> None:
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

    def test_only_complete_entries_get_a_place(self) -> None:
        drawn = draw_table.main_table(
            draw_table.ranked([entry("cheap", 3, draw_table.DESK_COUNT), entry("unfinished", 1, 5)])
        )
        self.assertTrue(drawn[2].startswith("| 1 | "))
        self.assertTrue(drawn[3].startswith("|  | "))


class TheDrawing(unittest.TestCase):
    def test_a_note_cannot_break_its_row(self) -> None:
        noted = entry("noted", 3, draw_table.DESK_COUNT)
        noted["result"]["notes"] = "one | two\nthree"
        row = draw_table.fine_print([noted])[2]
        self.assertIn("one \\| two three", row)

    def test_no_add_ons_reads_none_and_an_unrecorded_field_says_so(self) -> None:
        plain = entry("plain", 3, draw_table.DESK_COUNT)
        self.assertEqual(draw_table.addons(plain), "none")
        unrecorded = copy.deepcopy(plain)
        del unrecorded["build"]["addons"]
        self.assertEqual(draw_table.addons(unrecorded), draw_table.NOT_RECORDED)

    def test_an_approximate_cost_is_marked(self) -> None:
        about = entry("about", 2, draw_table.DESK_COUNT)
        about["cost"]["approximate"] = True
        self.assertEqual(draw_table.cost(about), "~$2.00")
        self.assertEqual(draw_table.cost(entry("exact", 2, draw_table.DESK_COUNT)), "$2.00")


class TheCheck(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.entries = Path(scratch.name) / "entries"
        self.table = Path(scratch.name) / "TABLE.md"
        shutil.copytree(draw_table.ENTRIES, self.entries)
        self.arguments = ["--entries", str(self.entries), "--table", str(self.table)]

    def test_the_committed_table_matches_the_committed_entries(self) -> None:
        self.assertEqual(draw_table.main(["--check"]), 0)

    def test_a_missing_or_stale_table_fails_the_check(self) -> None:
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)
        self.assertEqual(draw_table.main(self.arguments), 0)
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 0)
        self.table.write_text(self.table.read_text(encoding="utf-8") + "edited by hand\n")
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)

    def test_an_ill_formed_entry_fails_and_draws_nothing(self) -> None:
        (self.entries / "broken.toml").write_text('handle = "x"\n', encoding="utf-8")
        self.assertEqual(draw_table.main(self.arguments), 1)
        self.assertFalse(self.table.exists())

    def test_a_file_that_is_not_toml_fails(self) -> None:
        (self.entries / "broken.toml").write_text("handle = \n", encoding="utf-8")
        self.assertEqual(draw_table.main(["--check", *self.arguments]), 1)

    def test_the_template_is_not_drawn(self) -> None:
        self.assertEqual(draw_table.main(self.arguments), 0)
        self.assertNotIn("your-github-handle", self.table.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
