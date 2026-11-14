#!/usr/bin/env python3
"""Check a running book club against the Advent of Vibe 2026 assignment.

This exists so anyone can prove, with one command, that their book club does
what the assignment asks. It talks HTTP to a club and an observer that are
already running and knows nothing about the language they are written in.

    check_bookclub.py run --base-url http://127.0.0.1:8488 --observer-url http://127.0.0.1:8489
    (stop the club, throw its read model away, start it again)
    check_bookclub.py recheck --base-url http://127.0.0.1:8488

Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUITE_VERSION = "0.10.0"
DEFAULT_BASE_URL = "http://127.0.0.1:8488"
DEFAULT_OBSERVER_URL = "http://127.0.0.1:8489"
SCOREBOARD = "/api/scoreboard"
DEFAULT_WITNESS = "witness.json"
DEFAULT_PATIENCE_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 10.0
POLL_PAUSE_SECONDS = 0.1
ORDER_PAUSE_SECONDS = 0.01
RESTART_PATIENCE_SECONDS = 60.0
PARTY_EVERY = 5
EARLIEST_MOMENT_MS = 10**12

CLUB_NAME = "The Crooked Shelf"
ORGANISER = "ada"
MEMBER_NAME = "Bea"
BOOK_TITLE = "The Left Hand of Darkness"
BOOK_AUTHOR = "Ursula K. Le Guin"
PAGES_READ = 304

NOT_FOUND = {"ok": False, "error": "not_found"}


class Failed(Exception):
    """A check fails; the message says what the club did instead."""


@dataclass(frozen=True)
class Reply:
    status: int
    body: Any


class Club:
    """The running club, and the observer that watches it, reached over HTTP."""

    def __init__(
        self, base_url: str, patience: float, observer_url: str = DEFAULT_OBSERVER_URL
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.observer_url = observer_url.rstrip("/")
        self.patience = patience

    def scoreboard(self) -> Reply:
        return self._send(urllib.request.Request(self.observer_url + SCOREBOARD))

    def post(self, route: str, payload: dict[str, Any]) -> Reply:
        data = json.dumps(payload).encode()
        headers = {"content-type": "application/json"}
        return self._send(urllib.request.Request(self.base_url + route, data, headers))

    def get(self, route: str) -> Reply:
        return self._send(urllib.request.Request(self.base_url + route))

    def _send(self, request: urllib.request.Request) -> Reply:
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return Reply(response.status, _json_or_none(response.read()))
        except urllib.error.HTTPError as error:
            with error:
                return Reply(error.code, _json_or_none(error.read()))
        except OSError as error:
            raise Failed(f"the club did not answer {request.full_url}: {error}") from error

    def is_up(self) -> bool:
        try:
            self.get(f"/api/clubs/{new_id('bookclub')}")
        except Failed:
            return False
        return True


def _json_or_none(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# What a check expects of a reply
# ---------------------------------------------------------------------------


def expect(holds: bool, otherwise: str) -> None:
    if not holds:
        raise Failed(otherwise)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def well_formed(candidate: Any) -> bool:
    if not isinstance(candidate, str) or candidate.count("-") != 1:
        return False
    prefix, _, digits = candidate.partition("-")
    return (
        0 < len(prefix) <= 32
        and prefix.isascii()
        and prefix.isalpha()
        and prefix.islower()
        and len(digits) == 32
        and all(digit in "0123456789abcdef" for digit in digits)
    )


def accepted(reply: Reply, event_type: str, version: int) -> dict[str, Any]:
    """The club accepted a command: 200, the stream's new version, one event."""
    body = reply.body if isinstance(reply.body, dict) else {}
    expect(reply.status == 200, f"wanted 200 for {event_type}, got {reply.status} {reply.body}")
    expect(body.get("ok") is True, f"wanted ok true, got {reply.body}")
    expect(body.get("version") == version, f"wanted version {version}, got {body.get('version')}")
    events = body.get("events")
    expect(isinstance(events, list) and len(events) == 1, f"wanted one event, got {events}")
    event = events[0]
    expect(isinstance(event, dict), f"wanted an event object, got {event}")
    expect(event.get("event_type") == event_type, f"wanted {event_type}, got {event}")
    return event


def refused(reply: Reply, reason: str | None = None) -> None:
    """The club refused a command: 400, ok false, and the reason when one is named."""
    body = reply.body if isinstance(reply.body, dict) else {}
    wanted = reason or "a refusal"
    expect(reply.status == 400, f"wanted 400 ({wanted}), got {reply.status} {reply.body}")
    expect(body.get("ok") is False, f"wanted ok false ({wanted}), got {reply.body}")
    error = body.get("error")
    expect(isinstance(error, str) and error != "", f"wanted an error word, got {reply.body}")
    expect(reason is None or error == reason, f"wanted error {reason}, got {error}")


def carries(event: dict[str, Any], **wanted: Any) -> None:
    for field, value in wanted.items():
        expect(event.get(field) == value, f"wanted {field}={value!r} in {event}")


def moment(event: dict[str, Any], field: str) -> int:
    value = event.get(field)
    is_ms = isinstance(value, int) and not isinstance(value, bool) and value >= EARLIEST_MOMENT_MS
    expect(is_ms, f"wanted {field} as integer milliseconds since 1970, got {value!r}")
    return value


def answers(club: Club, route: str, **wanted: Any) -> dict[str, Any]:
    """The read model catches up: GET answers 200 with the wanted fields, within patience."""
    deadline = time.monotonic() + club.patience
    while True:
        reply = club.get(route)
        body = reply.body if isinstance(reply.body, dict) else {}
        if reply.status == 200 and all(body.get(f) == v for f, v in wanted.items()):
            return body
        if time.monotonic() >= deadline:
            raise Failed(f"GET {route}: wanted {wanted}, last answer {reply.status} {reply.body}")
        time.sleep(POLL_PAUSE_SECONDS)


def misses(club: Club, route: str) -> None:
    reply = club.get(route)
    expect(reply.status == 404, f"GET {route}: wanted 404, got {reply.status} {reply.body}")
    expect(reply.body == NOT_FOUND, f"GET {route}: wanted {NOT_FOUND}, got {reply.body}")


# ---------------------------------------------------------------------------
# Things a check needs before it can start
# ---------------------------------------------------------------------------


def initiated(club: Club) -> dict[str, Any]:
    payload = {"club_id": new_id("bookclub"), "name": CLUB_NAME, "initiated_by": ORGANISER}
    return accepted(club.post("/api/clubs/initiate", payload), "bookclub_initiated_v1", 0)


def seen_by_readers(club: Club, club_id: str) -> None:
    """Wait for the club's row: a registration and a book take the club's name from it."""
    answers(club, f"/api/clubs/{club_id}", club_id=club_id)


def registered(club: Club, club_id: str, name: str = MEMBER_NAME) -> dict[str, Any]:
    payload = {"club_id": club_id, "member_id": new_id("member"), "name": name}
    return accepted(club.post("/api/members/register", payload), "member_registered_v1", 0)


def procured(club: Club, club_id: str) -> dict[str, Any]:
    payload = {
        "club_id": club_id,
        "book_id": new_id("book"),
        "title": BOOK_TITLE,
        "author": BOOK_AUTHOR,
    }
    return accepted(club.post("/api/books/procure", payload), "book_procured_v1", 0)


def started(club: Club, member_id: str, book_id: str) -> dict[str, Any]:
    payload = {"reading_id": new_id("reading"), "member_id": member_id, "book_id": book_id}
    return accepted(club.post("/api/readings/start", payload), "reading_started_v1", 0)


def finished(club: Club, reading_id: str) -> dict[str, Any]:
    payload = {"reading_id": reading_id, "pages_read": PAGES_READ}
    return accepted(club.post("/api/readings/finish", payload), "reading_finished_v1", 1)


def a_reading(club: Club) -> dict[str, Any]:
    club_id = initiated(club)["club_id"]
    member = registered(club, club_id)
    book = procured(club, club_id)
    return started(club, member["member_id"], book["book_id"])


def unregistered(club: Club, member_id: str) -> dict[str, Any]:
    payload = {"member_id": member_id, "unregistered_by": ORGANISER}
    return accepted(club.post("/api/members/unregister", payload), "member_unregistered_v1", 1)


def retired(club: Club, book_id: str) -> dict[str, Any]:
    payload = {"book_id": book_id, "retired_by": ORGANISER}
    return accepted(club.post("/api/books/retire", payload), "book_retired_v1", 1)


def archived(club: Club, club_id: str, version: int = 1) -> dict[str, Any]:
    payload = {"club_id": club_id, "archived_by": ORGANISER}
    return accepted(club.post("/api/clubs/archive", payload), "bookclub_archived_v1", version)


def party(club: Club, club_id: str) -> int:
    """Plan one party by hand and return how many the club has now planned."""
    reply = club.post("/api/clubs/plan_party", {"club_id": club_id})
    body = reply.body if isinstance(reply.body, dict) else {}
    expect(reply.status == 200 and body.get("ok") is True, f"plan_party: got {reply.body}")
    events = body.get("events") or [{}]
    planned = events[0].get("parties_planned") if isinstance(events[0], dict) else None
    expect(isinstance(planned, int), f"wanted parties_planned as an integer, got {reply.body}")
    return planned


# ---------------------------------------------------------------------------
# The club's 23 desks, in the order they are built
# ---------------------------------------------------------------------------


def initiate_bookclub(club: Club) -> None:
    payload = {"club_id": new_id("bookclub"), "name": CLUB_NAME, "initiated_by": ORGANISER}
    event = accepted(club.post("/api/clubs/initiate", payload), "bookclub_initiated_v1", 0)
    carries(event, **payload)
    moment(event, "initiated_at")
    refused(club.post("/api/clubs/initiate", payload), "already_initiated")
    refused(club.post("/api/clubs/initiate", {"initiated_by": ORGANISER}))
    no_id = {"name": CLUB_NAME, "initiated_by": ORGANISER}
    minted = accepted(club.post("/api/clubs/initiate", no_id), "bookclub_initiated_v1", 0)
    expect(well_formed(minted.get("club_id")), f"wanted a minted club_id, got {minted}")


def bookclub_initiated_to_clubs(club: Club) -> None:
    event = initiated(club)
    answers(
        club,
        f"/api/clubs/{event['club_id']}",
        club_id=event["club_id"],
        name=CLUB_NAME,
        status="active",
        initiated_by=ORGANISER,
        initiated_at=event["initiated_at"],
    )


def get_bookclub_by_id(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    answers(club, f"/api/clubs/{club_id}", club_id=club_id)
    misses(club, f"/api/clubs/{new_id('bookclub')}")


def register_member(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    seen_by_readers(club, club_id)
    payload = {"club_id": club_id, "member_id": new_id("member"), "name": MEMBER_NAME}
    event = accepted(club.post("/api/members/register", payload), "member_registered_v1", 0)
    carries(event, club_name=CLUB_NAME, **payload)
    moment(event, "registered_at")
    refused(club.post("/api/members/register", payload), "already_registered")
    refused(club.post("/api/members/register", {"club_id": club_id}))
    no_id = {"club_id": club_id, "name": MEMBER_NAME}
    minted = accepted(club.post("/api/members/register", no_id), "member_registered_v1", 0)
    expect(well_formed(minted.get("member_id")), f"wanted a minted member_id, got {minted}")


def member_registered_to_members(club: Club) -> None:
    event = registered(club, initiated(club)["club_id"])
    answers(
        club,
        f"/api/members/{event['member_id']}",
        member_id=event["member_id"],
        club_id=event["club_id"],
        name=MEMBER_NAME,
        status="active",
        registered_at=event["registered_at"],
    )


def get_member_by_id(club: Club) -> None:
    member_id = registered(club, initiated(club)["club_id"])["member_id"]
    answers(club, f"/api/members/{member_id}", member_id=member_id)
    misses(club, f"/api/members/{new_id('member')}")


def procure_book(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    seen_by_readers(club, club_id)
    payload = {
        "club_id": club_id,
        "book_id": new_id("book"),
        "title": BOOK_TITLE,
        "author": BOOK_AUTHOR,
    }
    event = accepted(club.post("/api/books/procure", payload), "book_procured_v1", 0)
    carries(event, club_name=CLUB_NAME, **payload)
    moment(event, "procured_at")
    refused(club.post("/api/books/procure", payload), "already_procured")
    refused(club.post("/api/books/procure", {"club_id": club_id, "author": BOOK_AUTHOR}))
    no_id = {"club_id": club_id, "title": BOOK_TITLE, "author": BOOK_AUTHOR}
    minted = accepted(club.post("/api/books/procure", no_id), "book_procured_v1", 0)
    expect(well_formed(minted.get("book_id")), f"wanted a minted book_id, got {minted}")


def book_procured_to_books(club: Club) -> None:
    event = procured(club, initiated(club)["club_id"])
    answers(
        club,
        f"/api/books/{event['book_id']}",
        book_id=event["book_id"],
        club_id=event["club_id"],
        title=BOOK_TITLE,
        author=BOOK_AUTHOR,
        status="on_shelf",
        procured_at=event["procured_at"],
    )


def get_book_by_id(club: Club) -> None:
    book_id = procured(club, initiated(club)["club_id"])["book_id"]
    answers(club, f"/api/books/{book_id}", book_id=book_id)
    misses(club, f"/api/books/{new_id('book')}")


def start_reading(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    member_id = registered(club, club_id)["member_id"]
    book_id = procured(club, club_id)["book_id"]
    payload = {"reading_id": new_id("reading"), "member_id": member_id, "book_id": book_id}
    event = accepted(club.post("/api/readings/start", payload), "reading_started_v1", 0)
    carries(event, **payload)
    moment(event, "started_at")
    refused(club.post("/api/readings/start", payload), "already_started")
    refused(club.post("/api/readings/start", {"member_id": member_id}))
    no_id = {"member_id": member_id, "book_id": book_id}
    minted = accepted(club.post("/api/readings/start", no_id), "reading_started_v1", 0)
    expect(well_formed(minted.get("reading_id")), f"wanted a minted reading_id, got {minted}")


def reading_started_to_readings(club: Club) -> None:
    event = a_reading(club)
    answers(
        club,
        f"/api/readings/{event['reading_id']}",
        reading_id=event["reading_id"],
        member_id=event["member_id"],
        book_id=event["book_id"],
        status="in_progress",
        started_at=event["started_at"],
        pages_read=0,
        finished_at=None,
    )


def get_reading_by_id(club: Club) -> None:
    reading_id = a_reading(club)["reading_id"]
    answers(club, f"/api/readings/{reading_id}", reading_id=reading_id)
    misses(club, f"/api/readings/{new_id('reading')}")


def finish_reading(club: Club) -> None:
    reading = a_reading(club)
    reading_id = reading["reading_id"]
    payload = {"reading_id": reading_id, "pages_read": PAGES_READ}
    refused(club.post("/api/readings/finish", {"reading_id": reading_id, "pages_read": -1}))
    refused(club.post("/api/readings/finish", {"reading_id": reading_id, "pages_read": "many"}))
    event = accepted(club.post("/api/readings/finish", payload), "reading_finished_v1", 1)
    carries(
        event,
        member_id=reading["member_id"],
        book_id=reading["book_id"],
        started_at=reading["started_at"],
        **payload,
    )
    expect(moment(event, "finished_at") >= reading["started_at"], "finished before it started")
    refused(club.post("/api/readings/finish", payload), "finished")
    unknown = {"reading_id": new_id("reading"), "pages_read": PAGES_READ}
    refused(club.post("/api/readings/finish", unknown), "not_started")


def reading_finished_to_readings(club: Club) -> None:
    reading = a_reading(club)
    event = finished(club, reading["reading_id"])
    answers(
        club,
        f"/api/readings/{reading['reading_id']}",
        status="finished",
        started_at=reading["started_at"],
        pages_read=PAGES_READ,
        finished_at=event["finished_at"],
    )


def get_readings_by_member(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    reader = registered(club, club_id)["member_id"]
    someone_else = registered(club, club_id, "Cy")["member_id"]
    first = started(club, reader, procured(club, club_id)["book_id"])["reading_id"]
    time.sleep(ORDER_PAUSE_SECONDS)
    started(club, someone_else, procured(club, club_id)["book_id"])
    time.sleep(ORDER_PAUSE_SECONDS)
    second = started(club, reader, procured(club, club_id)["book_id"])["reading_id"]
    route = f"/api/members/{reader}/readings"
    deadline = time.monotonic() + club.patience
    while _reading_ids(club.get(route)) != [first, second]:
        expect(time.monotonic() < deadline, f"GET {route}: wanted {[first, second]} in order")
        time.sleep(POLL_PAUSE_SECONDS)
    nobody = club.get(f"/api/members/{new_id('member')}/readings")
    expect(nobody.status == 200 and nobody.body == [], f"wanted 200 [], got {nobody}")


def _reading_ids(reply: Reply) -> list[Any] | None:
    if reply.status != 200 or not isinstance(reply.body, list):
        return None
    return [row.get("reading_id") if isinstance(row, dict) else None for row in reply.body]


def plan_party(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    for count in (1, 2):
        reply = club.post("/api/clubs/plan_party", {"club_id": club_id})
        event = accepted(reply, "party_planned_v1", count)
        carries(event, club_id=club_id, parties_planned=count)
        moment(event, "planned_at")
    refused(club.post("/api/clubs/plan_party", {"club_id": new_id("bookclub")}), "not_initiated")


def on_member_registered_maybe_plan_party(club: Club) -> None:
    club_id = initiated(club)["club_id"]
    for number in range(PARTY_EVERY):
        registered(club, club_id, f"Member {number}")
    deadline = time.monotonic() + club.patience
    by_hand = 0
    while True:
        by_hand += 1
        by_policy = party(club, club_id) - by_hand
        expect(by_policy <= 1, f"five registrations planned {by_policy} parties, wanted one")
        if by_policy == 1:
            return
        expect(time.monotonic() < deadline, "five registrations in a row planned no party")
        time.sleep(POLL_PAUSE_SECONDS)


def unregister_member(club: Club) -> None:
    member = registered(club, initiated(club)["club_id"])
    payload = {"member_id": member["member_id"], "unregistered_by": ORGANISER}
    event = accepted(club.post("/api/members/unregister", payload), "member_unregistered_v1", 1)
    carries(
        event,
        club_id=member["club_id"],
        name=MEMBER_NAME,
        registered_at=member["registered_at"],
        **payload,
    )
    moment(event, "unregistered_at")
    refused(club.post("/api/members/unregister", payload), "unregistered")
    unknown = {"member_id": new_id("member"), "unregistered_by": ORGANISER}
    refused(club.post("/api/members/unregister", unknown), "not_registered")


def member_unregistered_to_members(club: Club) -> None:
    member = registered(club, initiated(club)["club_id"])
    unregistered(club, member["member_id"])
    answers(
        club,
        f"/api/members/{member['member_id']}",
        name=MEMBER_NAME,
        status="unregistered",
        registered_at=member["registered_at"],
    )


def retire_book(club: Club) -> None:
    book = procured(club, initiated(club)["club_id"])
    payload = {"book_id": book["book_id"], "retired_by": ORGANISER}
    event = accepted(club.post("/api/books/retire", payload), "book_retired_v1", 1)
    carries(
        event,
        club_id=book["club_id"],
        title=BOOK_TITLE,
        author=BOOK_AUTHOR,
        procured_at=book["procured_at"],
        **payload,
    )
    moment(event, "retired_at")
    refused(club.post("/api/books/retire", payload), "retired")
    unknown = {"book_id": new_id("book"), "retired_by": ORGANISER}
    refused(club.post("/api/books/retire", unknown), "not_procured")


def book_retired_to_books(club: Club) -> None:
    book = procured(club, initiated(club)["club_id"])
    retired(club, book["book_id"])
    answers(
        club,
        f"/api/books/{book['book_id']}",
        title=BOOK_TITLE,
        author=BOOK_AUTHOR,
        status="retired",
        procured_at=book["procured_at"],
    )


def archive_bookclub(club: Club) -> None:
    opened = initiated(club)
    payload = {"club_id": opened["club_id"], "archived_by": ORGANISER}
    event = accepted(club.post("/api/clubs/archive", payload), "bookclub_archived_v1", 1)
    carries(
        event,
        name=CLUB_NAME,
        initiated_by=ORGANISER,
        initiated_at=opened["initiated_at"],
        **payload,
    )
    moment(event, "archived_at")
    refused(club.post("/api/clubs/archive", payload), "archived")
    refused(club.post("/api/clubs/plan_party", {"club_id": opened["club_id"]}), "archived")
    unknown = {"club_id": new_id("bookclub"), "archived_by": ORGANISER}
    refused(club.post("/api/clubs/archive", unknown), "not_initiated")


def bookclub_archived_to_clubs(club: Club) -> None:
    opened = initiated(club)
    archived(club, opened["club_id"])
    answers(
        club,
        f"/api/clubs/{opened['club_id']}",
        name=CLUB_NAME,
        status="archived",
        initiated_by=ORGANISER,
        initiated_at=opened["initiated_at"],
    )


# ---------------------------------------------------------------------------
# The observer's four desks: a second service that only sees the club's facts
# ---------------------------------------------------------------------------


def _board_row(reply: Reply, club_id: str) -> dict[str, Any] | None:
    body = reply.body if isinstance(reply.body, dict) else {}
    clubs = body.get("clubs") if reply.status == 200 else None
    rows = clubs if isinstance(clubs, list) else []
    return next((r for r in rows if isinstance(r, dict) and r.get("club_id") == club_id), None)


def on_the_board(club: Club, club_id: str, **wanted: Any) -> dict[str, Any]:
    """The observer catches up: its scoreboard lists the club with the wanted fields."""
    deadline = time.monotonic() + club.patience
    while True:
        reply = club.scoreboard()
        row = _board_row(reply, club_id)
        if row is not None and all(row.get(f) == v for f, v in wanted.items()):
            return row
        if time.monotonic() >= deadline:
            seen = row if row is not None else f"{reply.status}, club not listed"
            raise Failed(f"GET {SCOREBOARD}: wanted club {club_id} with {wanted}, last: {seen}")
        time.sleep(POLL_PAUSE_SECONDS)


def a_club_with_a_member(club: Club) -> tuple[str, dict[str, Any]]:
    club_id = initiated(club)["club_id"]
    seen_by_readers(club, club_id)
    return club_id, registered(club, club_id)


def ingest_member_registered(club: Club) -> None:
    club_id, _ = a_club_with_a_member(club)
    time.sleep(ORDER_PAUSE_SECONDS)
    latest = registered(club, club_id, "Cy")
    on_the_board(
        club,
        club_id,
        club_name=CLUB_NAME,
        members=2,
        last_registered={"name": "Cy", "registered_at": latest["registered_at"]},
    )


def ingest_book_procured(club: Club) -> None:
    club_id, _ = a_club_with_a_member(club)
    for _ in range(2):
        procured(club, club_id)
    on_the_board(club, club_id, members=1, books_on_shelf=2, books_retired=0)


def ingest_book_retired(club: Club) -> None:
    club_id, _ = a_club_with_a_member(club)
    procured(club, club_id)
    retired(club, procured(club, club_id)["book_id"])
    on_the_board(club, club_id, books_on_shelf=1, books_retired=1)


def get_scoreboard(club: Club) -> None:
    club_id, _ = a_club_with_a_member(club)
    procured(club, club_id)
    on_the_board(club, club_id, members=1, books_on_shelf=1, bookclub_verified="yes")
    board = club.scoreboard().body
    rows = board["clubs"]
    ids = [row.get("club_id") for row in rows]
    expect(ids == sorted(ids), f"GET {SCOREBOARD}: wanted the clubs sorted by club_id")
    for total in ("members", "books_on_shelf", "books_retired"):
        listed = sum(row.get(total, 0) for row in rows)
        is_count = isinstance(board.get(total), int) and not isinstance(board.get(total), bool)
        expect(
            is_count, f"GET {SCOREBOARD}: wanted {total} as an integer, got {board.get(total)!r}"
        )
        expect(
            board[total] >= listed, f"GET {SCOREBOARD}: {total} is less than its clubs add up to"
        )


# ---------------------------------------------------------------------------
# The rebuild: the log is the truth
# ---------------------------------------------------------------------------


def leave_a_trace(club: Club) -> dict[str, Any]:
    """Run two clubs through their whole life and note what a reader is told.

    The closed club has ended everything it started. The open club has had the
    one party its five members earned, plus one planned by hand.
    """
    closed = initiated(club)["club_id"]
    member = registered(club, closed)["member_id"]
    book = procured(club, closed)["book_id"]
    reading = started(club, member, book)["reading_id"]
    finished(club, reading)
    unregistered(club, member)
    retired(club, book)
    archived(club, closed)

    open_club = initiated(club)["club_id"]
    stayer = [registered(club, open_club, f"Member {n}") for n in range(PARTY_EVERY)][0]
    parties = _parties_after_the_policy(club, open_club)

    wanted = {
        f"/api/clubs/{closed}": {"status": "archived"},
        f"/api/members/{member}": {"status": "unregistered"},
        f"/api/books/{book}": {"status": "retired"},
        f"/api/readings/{reading}": {"status": "finished", "pages_read": PAGES_READ},
        f"/api/clubs/{open_club}": {"status": "active"},
        f"/api/members/{stayer['member_id']}": {"status": "active"},
    }
    return {
        "told": {route: answers(club, route, **fields) for route, fields in wanted.items()},
        "closed_club": closed,
        "finished_reading": reading,
        "open_club": open_club,
        "registered_member": stayer["member_id"],
        "parties_planned": parties,
    }


def _parties_after_the_policy(club: Club, club_id: str) -> int:
    """Plan parties by hand until the policy's own party shows in the count."""
    deadline = time.monotonic() + club.patience
    by_hand = 0
    while True:
        by_hand += 1
        planned = party(club, club_id)
        if planned == by_hand + 1:
            return planned
        expect(time.monotonic() < deadline, "the policy's party never showed in the count")
        time.sleep(POLL_PAUSE_SECONDS)


def the_log_is_the_truth(club: Club, trace: dict[str, Any]) -> None:
    """After a restart without the read model, every answer is back and nothing happened twice."""
    for route, told in trace["told"].items():
        answers(club, route, **told)
    closed, open_club = trace["closed_club"], trace["open_club"]
    refused(club.post("/api/clubs/plan_party", {"club_id": closed}), "archived")
    again = {"club_id": open_club, "name": CLUB_NAME, "initiated_by": ORGANISER}
    refused(club.post("/api/clubs/initiate", again), "already_initiated")
    member = {"club_id": open_club, "member_id": trace["registered_member"], "name": MEMBER_NAME}
    refused(club.post("/api/members/register", member), "already_registered")
    reading = {"reading_id": trace["finished_reading"], "pages_read": PAGES_READ}
    refused(club.post("/api/readings/finish", reading), "finished")
    planned = trace["parties_planned"]
    for _ in range(2):
        wanted = planned + 1
        planned = party(club, open_club)
        expect(planned == wanted, f"wanted {wanted} parties after the restart, got {planned}")
        time.sleep(POLL_PAUSE_SECONDS)
    trace["parties_planned"] = planned


# ---------------------------------------------------------------------------
# The whole check
# ---------------------------------------------------------------------------

DESKS: tuple[Callable[[Club], None], ...] = (
    initiate_bookclub,
    bookclub_initiated_to_clubs,
    get_bookclub_by_id,
    register_member,
    member_registered_to_members,
    get_member_by_id,
    procure_book,
    book_procured_to_books,
    get_book_by_id,
    start_reading,
    reading_started_to_readings,
    get_reading_by_id,
    finish_reading,
    reading_finished_to_readings,
    get_readings_by_member,
    plan_party,
    on_member_registered_maybe_plan_party,
    unregister_member,
    member_unregistered_to_members,
    retire_book,
    book_retired_to_books,
    archive_bookclub,
    bookclub_archived_to_clubs,
    ingest_member_registered,
    ingest_book_procured,
    ingest_book_retired,
    get_scoreboard,
)
DESK_COUNT = len(DESKS)
REBUILD = the_log_is_the_truth.__name__
WAITS_FOR_RESTART = "not checked yet: restart the club without its read model, then run recheck"


def attempt(check: Callable[[], Any]) -> tuple[bool, str, Any]:
    try:
        return True, "", check()
    except Failed as failed:
        return False, str(failed), None


def check_desks(club: Club) -> dict[str, Any]:
    """Every desk, then the trace the rebuild will be checked against."""
    desks = {}
    for number, desk in enumerate(DESKS, start=1):
        passed, reason, _ = attempt(lambda desk=desk: desk(club))
        desks[str(number)] = {"name": desk.__name__, "passed": passed, "reason": reason}
    has_trace, reason, trace = attempt(lambda: leave_a_trace(club))
    waiting = WAITS_FOR_RESTART if has_trace else f"no trace to check against: {reason}"
    return {
        "suite": "advent-of-vibe-2026/check_bookclub",
        "suite_version": SUITE_VERSION,
        "base_url": club.base_url,
        "observer_url": club.observer_url,
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "desks": desks,
        "rebuild": {"name": REBUILD, "passed": False, "reason": waiting},
        "trace": trace,
    }


def check_rebuild(club: Club, witness: dict[str, Any]) -> dict[str, Any]:
    """The rebuild, against the trace an earlier run left in the witness."""
    trace = witness.get("trace")
    if trace is None:
        return witness
    passed, reason, _ = attempt(lambda: the_log_is_the_truth(club, trace))
    witness["rebuild"] = {"name": REBUILD, "passed": passed, "reason": reason}
    witness["rechecked_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return witness


def desks_passed(witness: dict[str, Any]) -> int:
    return sum(1 for desk in witness["desks"].values() if desk["passed"])


def rebuilds(witness: dict[str, Any]) -> bool:
    return witness["rebuild"]["passed"]


def _line(label: str, check: dict[str, Any]) -> str:
    mark = "pass" if check["passed"] else "FAIL"
    reason = f"  {check['reason']}" if check["reason"] else ""
    return f"{label:>7}  {mark}  {check['name']}{reason}"


def report(witness: dict[str, Any]) -> str:
    lines = [_line(number, desk) for number, desk in witness["desks"].items()]
    lines.append(_line("rebuild", witness["rebuild"]))
    rebuilt = "yes" if rebuilds(witness) else "no"
    lines.append(
        f"desks: {desks_passed(witness)} of {DESK_COUNT}, rebuilds from the log: {rebuilt} "
        f"(suite {witness['suite_version']})"
    )
    return "\n".join(lines)


def restart_with(command: str, club: Club) -> None:
    """Run the entrant's own restart command and wait for the club to answer again."""
    subprocess.run(command, shell=True, check=True)
    deadline = time.monotonic() + RESTART_PATIENCE_SECONDS
    while not club.is_up():
        expect(time.monotonic() < deadline, "the club did not come back after the restart")
        time.sleep(POLL_PAUSE_SECONDS)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _save(witness: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")


def _run(arguments: argparse.Namespace) -> int:
    """Exit 0 when every desk passes, and the rebuild too if it was checked in this run."""
    club = Club(arguments.base_url, arguments.patience, arguments.observer_url)
    witness = check_desks(club)
    _save(witness, arguments.witness)
    if arguments.restart_command:
        restart_with(arguments.restart_command, club)
        witness = check_rebuild(club, witness)
        _save(witness, arguments.witness)
    print(report(witness))
    rebuild_holds = rebuilds(witness) or not arguments.restart_command
    return 0 if desks_passed(witness) == DESK_COUNT and rebuild_holds else 1


def _recheck(arguments: argparse.Namespace) -> int:
    club = Club(arguments.base_url, arguments.patience)
    witness = json.loads(arguments.witness.read_text(encoding="utf-8"))
    witness = check_rebuild(club, witness)
    _save(witness, arguments.witness)
    print(report(witness))
    return 0 if desks_passed(witness) == DESK_COUNT and rebuilds(witness) else 1


def _desks(_arguments: argparse.Namespace) -> int:
    for number, desk in enumerate(DESKS, start=1):
        print(f"{number:>2}  {desk.__name__}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", action="version", version=SUITE_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="check every desk and leave a trace for the rebuild")
    run.add_argument(
        "--restart-command",
        help="a shell command that stops the club, removes its read model and starts it "
        "again; with it, the rebuild is checked in the same run",
    )
    run.set_defaults(action=_run)
    recheck = commands.add_parser("recheck", help="check the rebuild, after the restart")
    recheck.set_defaults(action=_recheck)
    for command in (run, recheck):
        command.add_argument("--base-url", default=DEFAULT_BASE_URL)
        command.add_argument("--observer-url", default=DEFAULT_OBSERVER_URL)
        command.add_argument("--witness", type=Path, default=Path(DEFAULT_WITNESS))
        command.add_argument("--patience", type=float, default=DEFAULT_PATIENCE_SECONDS)
    commands.add_parser("desks", help="list the desks").set_defaults(action=_desks)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        return arguments.action(arguments)
    except Failed as failed:
        print(f"stopped: {failed}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
