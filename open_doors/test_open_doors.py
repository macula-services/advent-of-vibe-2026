"""The suite, tested against the model club: every door opens on a sound club,
and each planted defect shuts the doors it should and no others."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

import model_club
import open_doors

PATIENCE_SECONDS = 0.5

COMMANDS = {1, 4, 7, 10, 13, 16, 18, 20, 22}
PROJECTIONS = {2, 5, 8, 11, 14, 19, 21, 23}
QUERIES = {3, 6, 9, 12, 15}
POLICY = 17
LAST = open_doors.LAST_DOOR

# defect -> the doors that must stay shut, and no others
SHUT_BY_DEFECT = {
    # no row for a new club: its projection, its query, the two commands that
    # take the club's name from the row, and the open club of the trace
    "clubs_row_never_written": {2, 3, 4, 7, LAST},
    "club_name_not_stamped": {4, 7},
    "miss_answers_200": {3, 6, 9, 12},
    "readings_out_of_order": {15},
    # the finished event carries the wrong start, and so does the row made from it
    "finish_forgets_started_at": {13, 14},
    "no_party_policy": {POLICY, LAST},
    "two_parties_per_five": {POLICY, LAST},
    "replay_forgets_the_end": {LAST},
    "policy_runs_on_replay": {LAST},
    "log_not_kept": {LAST},
    "never_says:already_initiated": {1, LAST},
    "never_says:already_registered": {4, LAST},
    "never_says:already_procured": {7},
    "never_says:already_started": {10},
    "never_says:finished": {13, LAST},
    "never_says:unregistered": {18},
    "never_says:retired": {20},
    "never_says:archived": {22, LAST},
}


class RunningModel:
    """The model club on a local port, with a restart that keeps only the log."""

    def __init__(self, log_path: Path, defects: frozenset[str]) -> None:
        self.log_path = log_path
        self.defects = defects
        self.server = model_club.serve(model_club.ModelClub(log_path, defects), 0)
        self.port = self.server.server_address[1]
        self._start()

    def _start(self) -> None:
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def restart(self) -> None:
        self.stop()
        self.server = model_club.serve(model_club.ModelClub(self.log_path, self.defects), self.port)
        self._start()


def shut_doors(defects: frozenset[str]) -> set[int]:
    """Run all 24 doors against a model with these defects; the numbers that stay shut."""
    with tempfile.TemporaryDirectory() as scratch:
        running = RunningModel(Path(scratch) / "club.log", defects)
        try:
            club = open_doors.Club(f"http://127.0.0.1:{running.port}", PATIENCE_SECONDS)
            witness = open_doors.open_desk_doors(club)
            running.restart()
            witness = open_doors.open_last_door(club, witness)
        finally:
            running.stop()
    return {int(number) for number, door in witness["doors"].items() if not door["open"]}


class TheCalendar(unittest.TestCase):
    def test_there_are_24_doors_and_each_kind_is_counted_once(self) -> None:
        self.assertEqual(len(open_doors.DOOR_NAMES), open_doors.DOOR_COUNT)
        self.assertEqual(len(set(open_doors.DOOR_NAMES)), open_doors.DOOR_COUNT)
        every_door = COMMANDS | PROJECTIONS | QUERIES | {POLICY, LAST}
        self.assertEqual(every_door, set(range(1, open_doors.DOOR_COUNT + 1)))

    def test_every_defect_the_model_offers_has_an_expectation(self) -> None:
        self.assertLessEqual(set(model_club.DEFECTS), set(SHUT_BY_DEFECT))


class ASoundClub(unittest.TestCase):
    def test_opens_every_door(self) -> None:
        self.assertEqual(shut_doors(frozenset()), set())

    def test_waits_at_door_24_until_the_restart(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            running = RunningModel(Path(scratch) / "club.log", frozenset())
            try:
                club = open_doors.Club(f"http://127.0.0.1:{running.port}", PATIENCE_SECONDS)
                witness = open_doors.open_desk_doors(club)
            finally:
                running.stop()
        self.assertEqual(open_doors.opened(witness), open_doors.DOOR_COUNT - 1)
        last = witness["doors"][str(LAST)]
        self.assertEqual(last["reason"], open_doors.WAITS_FOR_RESTART)

    def test_door_24_can_be_rechecked_twice(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            running = RunningModel(Path(scratch) / "club.log", frozenset())
            try:
                club = open_doors.Club(f"http://127.0.0.1:{running.port}", PATIENCE_SECONDS)
                witness = open_doors.open_desk_doors(club)
                for _ in range(2):
                    running.restart()
                    witness = open_doors.open_last_door(club, witness)
                    self.assertEqual(open_doors.opened(witness), open_doors.DOOR_COUNT)
            finally:
                running.stop()


class ABrokenClub(unittest.TestCase):
    def test_each_defect_shuts_its_doors_and_no_others(self) -> None:
        for defect, wanted in SHUT_BY_DEFECT.items():
            with self.subTest(defect=defect):
                self.assertEqual(shut_doors(frozenset({defect})), wanted)


class NoClubAtAll(unittest.TestCase):
    def test_every_door_stays_shut(self) -> None:
        club = open_doors.Club("http://127.0.0.1:9", PATIENCE_SECONDS)
        witness = open_doors.open_desk_doors(club)
        self.assertEqual(open_doors.opened(witness), 0)


class Ids(unittest.TestCase):
    def test_a_minted_id_is_well_formed(self) -> None:
        self.assertTrue(open_doors.well_formed(open_doors.new_id("bookclub")))

    def test_ill_formed_ids_are_told_apart(self) -> None:
        hexes = "0123456789abcdef" * 2
        for candidate in (f"Club-{hexes}", f"club-{hexes[:-1]}", f"club-{hexes.upper()}", hexes, 7):
            with self.subTest(candidate=candidate):
                self.assertFalse(open_doors.well_formed(candidate))


if __name__ == "__main__":
    unittest.main()
