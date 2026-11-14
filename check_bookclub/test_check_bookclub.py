"""The suite, tested against the model club: a sound club passes every check,
and each planted defect fails the checks it should and no others."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

import check_bookclub
import model_club

PATIENCE_SECONDS = 0.5

COMMANDS = {1, 4, 7, 10, 13, 16, 18, 20, 22}
PROJECTIONS = {2, 5, 8, 11, 14, 19, 21, 23}
QUERIES = {3, 6, 9, 12, 15}
POLICY = 17
OBSERVER = {24, 25, 26, 27}
REBUILD = "rebuild"

# defect -> the desks (and the rebuild) that must fail, and no others
FAILED_BY_DEFECT = {
    # no row for a new club: its projection, its query, the two commands that
    # take the club's name from the row, the open club of the trace, and the
    # observer's desks, which all start from a club readers can see
    "clubs_row_never_written": {2, 3, 4, 7, REBUILD} | OBSERVER,
    # the fact carries no club name either, so the scoreboard cannot show it
    "club_name_not_stamped": {4, 7, 24},
    "miss_answers_200": {3, 6, 9, 12},
    "readings_out_of_order": {15},
    # the finished event carries the wrong start, and so does the row made from it
    "finish_forgets_started_at": {13, 14},
    "no_party_policy": {POLICY, REBUILD},
    "two_parties_per_five": {POLICY, REBUILD},
    "replay_forgets_the_end": {REBUILD},
    "policy_runs_on_replay": {REBUILD},
    "log_not_kept": {REBUILD},
    "no_facts_published": OBSERVER,
    "observer_ignores_retirement": {26},
    "observer_forgets_the_club_name": {24},
    "observer_never_verifies": {27},
    "never_says:already_initiated": {1, REBUILD},
    "never_says:already_registered": {4, REBUILD},
    "never_says:already_procured": {7},
    "never_says:already_started": {10},
    "never_says:finished": {13, REBUILD},
    "never_says:unregistered": {18},
    "never_says:retired": {20},
    "never_says:archived": {22, REBUILD},
}


class RunningModel:
    """The model club on a local port, with a restart that keeps only the log."""

    def __init__(self, log_path: Path, defects: frozenset[str]) -> None:
        self.log_path = log_path
        self.defects = defects
        self.model = model_club.ModelClub(log_path, defects)
        self.server = model_club.serve(self.model, 0)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.observer = model_club.ModelObserver(self.url, defects)
        self.observer_server = model_club.serve_observer(self.observer, 0)
        self.observer_url = f"http://127.0.0.1:{self.observer_server.server_address[1]}"
        self.observer_thread = threading.Thread(
            target=self.observer_server.serve_forever, daemon=True
        )
        self.observer_thread.start()
        self._start()

    def _start(self) -> None:
        self.model.subscribers.append(self.observer.receive)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _stop_club(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def stop(self) -> None:
        self._stop_club()
        self.observer_server.shutdown()
        self.observer_server.server_close()
        self.observer_thread.join()

    def restart(self) -> None:
        """Only the club restarts; the observer keeps running, as a separate service does."""
        self._stop_club()
        self.model = model_club.ModelClub(self.log_path, self.defects)
        self.server = model_club.serve(self.model, self.port)
        self._start()

    def club(self) -> check_bookclub.Club:
        return check_bookclub.Club(self.url, PATIENCE_SECONDS, self.observer_url)


def failed_checks(defects: frozenset[str]) -> set[int | str]:
    """Run the whole check against a model with these defects; what fails."""
    with tempfile.TemporaryDirectory() as scratch:
        running = RunningModel(Path(scratch) / "club.log", defects)
        try:
            club = running.club()
            witness = check_bookclub.check_desks(club)
            running.restart()
            witness = check_bookclub.check_rebuild(club, witness)
        finally:
            running.stop()
    failed: set[int | str] = {
        int(number) for number, desk in witness["desks"].items() if not desk["passed"]
    }
    return failed if check_bookclub.rebuilds(witness) else failed | {REBUILD}


class TheDesks(unittest.TestCase):
    def test_every_desk_is_checked_once_and_each_kind_is_counted(self) -> None:
        names = [desk.__name__ for desk in check_bookclub.DESKS]
        self.assertEqual(len(set(names)), check_bookclub.DESK_COUNT)
        every_desk = COMMANDS | PROJECTIONS | QUERIES | {POLICY} | OBSERVER
        self.assertEqual(every_desk, set(range(1, check_bookclub.DESK_COUNT + 1)))

    def test_every_defect_the_model_offers_has_an_expectation(self) -> None:
        self.assertLessEqual(set(model_club.DEFECTS), set(FAILED_BY_DEFECT))


class ASoundClub(unittest.TestCase):
    def test_passes_every_check(self) -> None:
        self.assertEqual(failed_checks(frozenset()), set())

    def test_the_rebuild_waits_for_the_restart(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            running = RunningModel(Path(scratch) / "club.log", frozenset())
            try:
                club = running.club()
                witness = check_bookclub.check_desks(club)
            finally:
                running.stop()
        self.assertEqual(check_bookclub.desks_passed(witness), check_bookclub.DESK_COUNT)
        self.assertFalse(check_bookclub.rebuilds(witness))
        self.assertEqual(witness["rebuild"]["reason"], check_bookclub.WAITS_FOR_RESTART)

    def test_the_rebuild_can_be_rechecked_twice(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            running = RunningModel(Path(scratch) / "club.log", frozenset())
            try:
                club = running.club()
                witness = check_bookclub.check_desks(club)
                for _ in range(2):
                    running.restart()
                    witness = check_bookclub.check_rebuild(club, witness)
                    self.assertTrue(check_bookclub.rebuilds(witness))
            finally:
                running.stop()

    def test_the_report_ends_with_both_results(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            running = RunningModel(Path(scratch) / "club.log", frozenset())
            try:
                club = running.club()
                witness = check_bookclub.check_desks(club)
            finally:
                running.stop()
        last_line = check_bookclub.report(witness).splitlines()[-1]
        count = check_bookclub.DESK_COUNT
        self.assertTrue(
            last_line.startswith(f"desks: {count} of {count}, rebuilds from the log: no")
        )


class ABrokenClub(unittest.TestCase):
    def test_each_defect_fails_its_checks_and_no_others(self) -> None:
        for defect, wanted in FAILED_BY_DEFECT.items():
            with self.subTest(defect=defect):
                self.assertEqual(failed_checks(frozenset({defect})), wanted)


class NoClubAtAll(unittest.TestCase):
    def test_every_check_fails(self) -> None:
        nowhere = "http://127.0.0.1:9"
        club = check_bookclub.Club(nowhere, PATIENCE_SECONDS, nowhere)
        witness = check_bookclub.check_desks(club)
        self.assertEqual(check_bookclub.desks_passed(witness), 0)
        self.assertFalse(check_bookclub.rebuilds(witness))


class Ids(unittest.TestCase):
    def test_a_minted_id_is_well_formed(self) -> None:
        self.assertTrue(check_bookclub.well_formed(check_bookclub.new_id("bookclub")))

    def test_ill_formed_ids_are_told_apart(self) -> None:
        hexes = "0123456789abcdef" * 2
        for candidate in (f"Club-{hexes}", f"club-{hexes[:-1]}", f"club-{hexes.upper()}", hexes, 7):
            with self.subTest(candidate=candidate):
                self.assertFalse(check_bookclub.well_formed(candidate))


if __name__ == "__main__":
    unittest.main()
