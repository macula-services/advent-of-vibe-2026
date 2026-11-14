"""The stranger test, tested on small trees built for the purpose."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import stranger_test

EVERYTHING_A_STRANGER_LOOKS_FOR = (
    len(stranger_test.COMMANDS) + len(stranger_test.QUERIES) + len(stranger_test.PROJECTIONS) + 1
)


def a_club_that_screams(root: Path, style: str = "snake") -> None:
    """One folder per command, one file per projection, question and policy."""
    names = [
        *stranger_test.COMMANDS,
        *stranger_test.QUERIES,
        *(f"{event}_v1_to_{table}" for event, table in stranger_test.PROJECTIONS),
        "on_member_registered_v1_maybe_plan_party",
    ]
    for name in names:
        (root / "src" / spelled(name, style)).mkdir(parents=True)


def spelled(name: str, style: str) -> str:
    parts = name.split("_")
    return {
        "snake": name,
        "kebab": "-".join(parts),
        "pascal": "".join(part.capitalize() for part in parts),
    }[style]


class TheStrangerTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_an_empty_checkout_fails_on_everything_a_stranger_looks_for(self) -> None:
        found = stranger_test.findings(self.root)
        self.assertEqual(len(found), EVERYTHING_A_STRANGER_LOOKS_FOR)
        self.assertEqual(stranger_test.main([str(self.root)]), 1)

    def test_a_club_that_screams_passes_in_any_spelling(self) -> None:
        for style in ("snake", "kebab", "pascal"):
            with self.subTest(style=style), tempfile.TemporaryDirectory() as scratch:
                a_club_that_screams(Path(scratch), style)
                self.assertEqual(stranger_test.findings(Path(scratch)), [])
                self.assertEqual(stranger_test.main([scratch]), 0)

    def test_one_missing_desk_is_named(self) -> None:
        a_club_that_screams(self.root)
        (self.root / "src" / "retire_book").rmdir()
        self.assertEqual(
            stranger_test.findings(self.root),
            ["no file or folder is named after the command retire_book"],
        )

    def test_unregister_member_does_not_stand_in_for_register_member(self) -> None:
        a_club_that_screams(self.root)
        (self.root / "src" / "register_member").rmdir()
        self.assertEqual(
            stranger_test.findings(self.root),
            ["no file or folder is named after the command register_member"],
        )

    def test_a_projection_needs_its_event_and_its_table(self) -> None:
        a_club_that_screams(self.root)
        (self.root / "src" / "book_retired_v1_to_books").rmdir()
        (self.root / "src" / "book_retired_v1").mkdir()
        self.assertEqual(
            stranger_test.findings(self.root),
            ["no file or folder says that book_retired is projected to books"],
        )

    def test_a_layer_folder_fails(self) -> None:
        a_club_that_screams(self.root)
        for layer in sorted(stranger_test.LAYER_FOLDERS):
            (self.root / "src" / layer).mkdir()
        found = stranger_test.findings(self.root)
        self.assertEqual(len(found), len(stranger_test.LAYER_FOLDERS))
        self.assertIn("src/services/ sorts code by technical kind", found)

    def test_a_file_named_like_a_layer_is_not_a_layer_folder(self) -> None:
        a_club_that_screams(self.root)
        (self.root / "src" / "events").write_text("", encoding="utf-8")
        self.assertEqual(stranger_test.findings(self.root), [])

    def test_a_row_change_name_fails(self) -> None:
        a_club_that_screams(self.root)
        (self.root / "src" / "MemberCreated.cs").write_text("", encoding="utf-8")
        (self.root / "src" / "book_updated_v1.erl").write_text("", encoding="utf-8")
        found = stranger_test.findings(self.root)
        self.assertEqual(
            found,
            [
                "src/MemberCreated.cs is named after a row change (created)",
                "src/book_updated_v1.erl is named after a row change (updated)",
            ],
        )

    def test_dependencies_and_hidden_folders_are_not_read(self) -> None:
        a_club_that_screams(self.root)
        for foreign in ("node_modules", ".git", "_build"):
            (self.root / foreign / "services").mkdir(parents=True)
            (self.root / foreign / "user_created.js").write_text("", encoding="utf-8")
        self.assertEqual(stranger_test.findings(self.root), [])

    def test_a_path_that_is_not_a_folder_is_refused(self) -> None:
        self.assertEqual(stranger_test.main([str(self.root / "nowhere")]), 2)


if __name__ == "__main__":
    unittest.main()
