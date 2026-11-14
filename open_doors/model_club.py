#!/usr/bin/env python3
"""A model book club in one file, for testing the suite itself.

This exists so the suite can be shown to catch a broken club: the model can be
started with a named defect, and the suite's own tests assert which door stays
shut. It is NOT an entry and not an example to copy: one file holding every
desk is exactly what the assignment forbids.

    model_club.py --port 8488 --log club.log [--defect no_party_policy]

The log file is the event log. The read model lives in memory, so every
restart rebuilds it from the log.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PARTY_EVERY = 5
NOT_FOUND = {"ok": False, "error": "not_found"}
UNKNOWN_ROUTE = {"error": "not_found"}
MISSING = "missing_required_fields"

# kind of dossier: the event that opens it, the event that ends it, and the
# three refusals (not opened yet, opened already, ended).
LIVES = {
    "club": ("bookclub_archived_v1", "not_initiated", "already_initiated", "archived"),
    "member": ("member_unregistered_v1", "not_registered", "already_registered", "unregistered"),
    "book": ("book_retired_v1", "not_procured", "already_procured", "retired"),
    "reading": ("reading_finished_v1", "not_started", "already_started", "finished"),
}
ENDINGS = frozenset(life[0] for life in LIVES.values())

DEFECTS = (
    "clubs_row_never_written",
    "club_name_not_stamped",
    "miss_answers_200",
    "readings_out_of_order",
    "finish_forgets_started_at",
    "no_party_policy",
    "two_parties_per_five",
    "replay_forgets_the_end",
    "policy_runs_on_replay",
    "log_not_kept",
)
NEVER_SAYS = "never_says:"


class Refused(Exception):
    """A command is refused; the message is the error word."""


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def text(params: dict[str, Any], field: str) -> str:
    value = params.get(field)
    if not isinstance(value, str) or value == "":
        raise Refused(MISSING)
    return value


def minted_or_own(params: dict[str, Any], field: str, prefix: str) -> str:
    if field not in params:
        return f"{prefix}-{uuid.uuid4().hex}"
    return text(params, field)


def echo(event: dict[str, Any], *fields: str) -> dict[str, Any]:
    return {field: event[field] for field in fields}


class ModelClub:
    def __init__(self, log_path: Path, defects: frozenset[str] = frozenset()) -> None:
        self.log_path = log_path
        self.defects = defects
        self.streams: dict[str, list[dict[str, Any]]] = {}
        self.tables: dict[str, dict[str, dict[str, Any]]] = {
            "clubs": {},
            "members": {},
            "books": {},
            "readings": {},
        }
        self.registrations = 0
        self.lock = threading.Lock()
        self._replay()

    def has(self, defect: str) -> bool:
        return defect in self.defects

    def _replay(self) -> None:
        if not self.log_path.exists():
            return
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            self.streams.setdefault(record["stream"], []).append(record["event"])
            self._project(record["event"], replaying=True)
            if self.has("policy_runs_on_replay"):
                self._react(record["event"])

    def record(self, stream_id: str, event: dict[str, Any]) -> int:
        stream = self.streams.setdefault(stream_id, [])
        stream.append(event)
        version = len(stream) - 1
        if not self.has("log_not_kept"):
            with self.log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"stream": stream_id, "event": event}) + "\n")
        self._project(event, replaying=False)
        self._react(event)
        return version

    def dossier(self, kind: str, stream_id: str, *, opening: bool = False) -> list[dict[str, Any]]:
        """The stream, if this command may add to it; a refusal otherwise."""
        ending, not_yet, already, over = LIVES[kind]
        stream = self.streams.get(stream_id, [])
        if any(event["event_type"] == ending for event in stream):
            self._refuse(over)
        if opening and stream:
            self._refuse(already)
        if not opening and not stream:
            raise Refused(not_yet)
        return stream

    def _refuse(self, word: str) -> None:
        if not self.has(NEVER_SAYS + word):
            raise Refused(word)

    def _project(self, event: dict[str, Any], *, replaying: bool) -> None:
        kind = event["event_type"]
        if replaying and kind in ENDINGS and self.has("replay_forgets_the_end"):
            return
        if kind == "bookclub_initiated_v1" and self.has("clubs_row_never_written"):
            return
        projection = PROJECTIONS.get(kind)
        if projection:
            projection(self.tables, event)

    def _react(self, event: dict[str, Any]) -> None:
        """The policy: every fifth registration plans a party for that member's club."""
        if event["event_type"] != "member_registered_v1" or self.has("no_party_policy"):
            return
        self.registrations += 1
        if self.registrations % PARTY_EVERY:
            return
        for _ in range(2 if self.has("two_parties_per_five") else 1):
            try:
                stream_id, planned = plan_party(self, {"club_id": event["club_id"]})
            except Refused:
                return
            self.record(stream_id, planned)

    def readings_of(self, member_id: str) -> list[dict[str, Any]]:
        rows = [row for row in self.tables["readings"].values() if row["member_id"] == member_id]
        latest_first = self.has("readings_out_of_order")
        return sorted(rows, key=lambda row: row["started_at"], reverse=latest_first)


# ---------------------------------------------------------------------------
# The nine commands
# ---------------------------------------------------------------------------


def initiate_bookclub(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    club_id = minted_or_own(params, "club_id", "bookclub")
    event = {
        "event_type": "bookclub_initiated_v1",
        "club_id": club_id,
        "name": text(params, "name"),
        "initiated_by": text(params, "initiated_by"),
        "initiated_at": now_ms(),
    }
    model.dossier("club", club_id, opening=True)
    return club_id, event


def archive_bookclub(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    club_id, archived_by = text(params, "club_id"), text(params, "archived_by")
    born = model.dossier("club", club_id)[0]
    return club_id, {
        "event_type": "bookclub_archived_v1",
        **echo(born, "club_id", "name", "initiated_by", "initiated_at"),
        "archived_by": archived_by,
        "archived_at": now_ms(),
    }


def plan_party(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    club_id = text(params, "club_id")
    stream = model.dossier("club", club_id)
    before = sum(1 for event in stream if event["event_type"] == "party_planned_v1")
    return club_id, {
        "event_type": "party_planned_v1",
        "club_id": club_id,
        "parties_planned": before + 1,
        "planned_at": now_ms(),
    }


def _club_name(model: ModelClub, club_id: str) -> str:
    if model.has("club_name_not_stamped"):
        return ""
    return model.tables["clubs"].get(club_id, {}).get("name", "")


def register_member(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    member_id = minted_or_own(params, "member_id", "member")
    club_id = text(params, "club_id")
    event = {
        "event_type": "member_registered_v1",
        "member_id": member_id,
        "club_id": club_id,
        "name": text(params, "name"),
        "club_name": _club_name(model, club_id),
        "registered_at": now_ms(),
    }
    model.dossier("member", member_id, opening=True)
    return member_id, event


def unregister_member(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    member_id, unregistered_by = text(params, "member_id"), text(params, "unregistered_by")
    born = model.dossier("member", member_id)[0]
    return member_id, {
        "event_type": "member_unregistered_v1",
        **echo(born, "member_id", "club_id", "name", "registered_at"),
        "unregistered_by": unregistered_by,
        "unregistered_at": now_ms(),
    }


def procure_book(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    book_id = minted_or_own(params, "book_id", "book")
    club_id = text(params, "club_id")
    event = {
        "event_type": "book_procured_v1",
        "book_id": book_id,
        "club_id": club_id,
        "title": text(params, "title"),
        "author": text(params, "author"),
        "club_name": _club_name(model, club_id),
        "procured_at": now_ms(),
    }
    model.dossier("book", book_id, opening=True)
    return book_id, event


def retire_book(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    book_id, retired_by = text(params, "book_id"), text(params, "retired_by")
    born = model.dossier("book", book_id)[0]
    return book_id, {
        "event_type": "book_retired_v1",
        **echo(born, "book_id", "club_id", "title", "author", "procured_at", "club_name"),
        "retired_by": retired_by,
        "retired_at": now_ms(),
    }


def start_reading(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    reading_id = minted_or_own(params, "reading_id", "reading")
    event = {
        "event_type": "reading_started_v1",
        "reading_id": reading_id,
        "member_id": text(params, "member_id"),
        "book_id": text(params, "book_id"),
        "started_at": now_ms(),
    }
    model.dossier("reading", reading_id, opening=True)
    return reading_id, event


def finish_reading(model: ModelClub, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    reading_id, pages = text(params, "reading_id"), params.get("pages_read")
    if not isinstance(pages, int) or isinstance(pages, bool) or pages < 0:
        raise Refused("invalid_params")
    born = model.dossier("reading", reading_id)[0]
    finished_at = now_ms()
    event = {
        "event_type": "reading_finished_v1",
        **echo(born, "reading_id", "member_id", "book_id", "started_at"),
        "pages_read": pages,
        "finished_at": finished_at,
    }
    if model.has("finish_forgets_started_at"):
        event["started_at"] = finished_at
    return reading_id, event


Command = Callable[[ModelClub, dict[str, Any]], tuple[str, dict[str, Any]]]
COMMANDS: dict[str, Command] = {
    "/api/clubs/initiate": initiate_bookclub,
    "/api/clubs/archive": archive_bookclub,
    "/api/clubs/plan_party": plan_party,
    "/api/members/register": register_member,
    "/api/members/unregister": unregister_member,
    "/api/books/procure": procure_book,
    "/api/books/retire": retire_book,
    "/api/readings/start": start_reading,
    "/api/readings/finish": finish_reading,
}


# ---------------------------------------------------------------------------
# The eight projections
# ---------------------------------------------------------------------------

Tables = dict[str, dict[str, dict[str, Any]]]


def _row(
    table: str, key: str, status: str, *fields: str
) -> Callable[[Tables, dict[str, Any]], None]:
    def write(tables: Tables, event: dict[str, Any]) -> None:
        tables[table][event[key]] = {**echo(event, key, *fields), "status": status}

    return write


def _reading_started(tables: Tables, event: dict[str, Any]) -> None:
    row = echo(event, "reading_id", "member_id", "book_id", "started_at")
    tables["readings"][event["reading_id"]] = {
        **row,
        "status": "in_progress",
        "pages_read": 0,
        "finished_at": None,
    }


PROJECTIONS: dict[str, Callable[[Tables, dict[str, Any]], None]] = {
    "bookclub_initiated_v1": _row(
        "clubs", "club_id", "active", "name", "initiated_by", "initiated_at"
    ),
    "bookclub_archived_v1": _row(
        "clubs", "club_id", "archived", "name", "initiated_by", "initiated_at"
    ),
    "member_registered_v1": _row(
        "members", "member_id", "active", "club_id", "name", "registered_at"
    ),
    "member_unregistered_v1": _row(
        "members", "member_id", "unregistered", "club_id", "name", "registered_at"
    ),
    "book_procured_v1": _row(
        "books", "book_id", "on_shelf", "club_id", "title", "author", "procured_at"
    ),
    "book_retired_v1": _row(
        "books", "book_id", "retired", "club_id", "title", "author", "procured_at"
    ),
    "reading_started_v1": _reading_started,
    "reading_finished_v1": _row(
        "readings",
        "reading_id",
        "finished",
        "member_id",
        "book_id",
        "started_at",
        "pages_read",
        "finished_at",
    ),
}


# ---------------------------------------------------------------------------
# The HTTP door
# ---------------------------------------------------------------------------


def write(model: ModelClub, route: str, params: Any) -> tuple[int, Any]:
    command = COMMANDS.get(route)
    if command is None:
        return 404, UNKNOWN_ROUTE
    try:
        stream_id, event = command(model, params if isinstance(params, dict) else {})
    except Refused as refusal:
        return 400, {"ok": False, "error": str(refusal)}
    version = model.record(stream_id, event)
    return 200, {"ok": True, "version": version, "events": [event]}


def read(model: ModelClub, route: str) -> tuple[int, Any]:
    parts = route.strip("/").split("/")
    if len(parts) == 4 and parts[:2] == ["api", "members"] and parts[3] == "readings":
        return 200, model.readings_of(parts[2])
    if len(parts) != 3 or parts[0] != "api" or parts[1] not in model.tables:
        return 404, UNKNOWN_ROUTE
    row = model.tables[parts[1]].get(parts[2])
    if row is not None:
        return 200, row
    return (200, {}) if model.has("miss_answers_200") else (404, NOT_FOUND)


def _handler(model: ModelClub) -> type[BaseHTTPRequestHandler]:
    class Door(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            raw = self.rfile.read(int(self.headers.get("content-length") or 0))
            try:
                params = json.loads(raw)
            except ValueError:
                params = {}
            with model.lock:
                self._reply(*write(model, self.path, params))

        def do_GET(self) -> None:
            with model.lock:
                self._reply(*read(model, self.path))

        def _reply(self, status: int, body: Any) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_: Any) -> None:
            pass

    return Door


def serve(model: ModelClub, port: int) -> ThreadingHTTPServer:
    """A server for the model, bound and ready; the caller runs serve_forever."""
    return ThreadingHTTPServer(("127.0.0.1", port), _handler(model))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8488)
    parser.add_argument("--log", type=Path, required=True, help="the event log file")
    parser.add_argument(
        "--defect",
        action="append",
        default=[],
        help=f"one of {', '.join(DEFECTS)}, or {NEVER_SAYS}<refusal word>; repeatable",
    )
    arguments = parser.parse_args()
    server = serve(ModelClub(arguments.log, frozenset(arguments.defect)), arguments.port)
    print(f"model club on http://127.0.0.1:{server.server_address[1]}, log in {arguments.log}")
    server.serve_forever()


if __name__ == "__main__":
    main()
