# The HTTP contract

*This exists so one check suite can knock on every club, whatever it is written in.*

Your club listens on HTTP and speaks JSON. The suite's default address is `http://127.0.0.1:8488`; any address works with `--base-url`. There is no authentication: the club runs on your own machine while it is checked.

## The rules that hold everywhere

**Ids.** An id is a lowercase word, a dash, and 32 lowercase hexadecimal digits: `member-3f2a…` (the pattern is `^[a-z]{1,32}-[a-f0-9]{32}$`). A caller may bring its own id when it opens a dossier. When it brings none, the club mints one.

**Moments.** Every `_at` field is an integer: milliseconds since 1 January 1970, UTC.

**A command that is accepted** answers `200`:

```json
{"ok": true, "version": 0, "events": [{"event_type": "member_registered_v1", "member_id": "member-…", "…": "…"}]}
```

`version` is the position of the new event in its own dossier's stream, counted from 0. The first event of a dossier has version 0, the second has version 1. `events` holds the one event the command produced, as a flat object: its `event_type` and its fields side by side.

**A command that is refused** answers `400`:

```json
{"ok": false, "error": "already_registered"}
```

For a refusal on business grounds the `error` word is fixed, and the tables below give it. For input that is missing or of the wrong type the status is `400` and `ok` is `false`; the word is yours to choose.

**A question** answers `200` with the row as a JSON object, or `404` with:

```json
{"ok": false, "error": "not_found"}
```

**Read models catch up.** A row may appear a moment after its command was accepted. The suite waits up to five seconds for it (`--patience`).

**Extra fields** in an event or a row are allowed. The fields named here must be there, with these names and these values.

## The life of a dossier

The same three refusals guard all four dossiers.

| Dossier | Opening it twice | Using it before it is opened | Using it after it has ended |
|---|---|---|---|
| Club | `already_initiated` | `not_initiated` | `archived` |
| Member | `already_registered` | `not_registered` | `unregistered` |
| Book | `already_procured` | `not_procured` | `retired` |
| Reading | `already_started` | `not_started` | `finished` |

Commands do not check one dossier against another. Registering a member in a club that does not exist is not refused, and the suite never does it.

## The nine commands

Fields in brackets are optional.

### `POST /api/clubs/initiate`

| | |
|---|---|
| Body | `name`, `initiated_by`, [`club_id`] |
| Event | `bookclub_initiated_v1`: `club_id`, `name`, `initiated_by`, `initiated_at` |
| Refused | `already_initiated` |

### `POST /api/members/register`

| | |
|---|---|
| Body | `club_id`, `name`, [`member_id`] |
| Event | `member_registered_v1`: `member_id`, `club_id`, `name`, `club_name`, `registered_at` |
| Refused | `already_registered` |

`club_name` is the name of the club, looked up from the clubs read model when the command comes in. It makes the event readable without a second lookup.

### `POST /api/books/procure`

| | |
|---|---|
| Body | `club_id`, `title`, `author`, [`book_id`] |
| Event | `book_procured_v1`: `book_id`, `club_id`, `title`, `author`, `club_name`, `procured_at` |
| Refused | `already_procured` |

### `POST /api/readings/start`

| | |
|---|---|
| Body | `member_id`, `book_id`, [`reading_id`] |
| Event | `reading_started_v1`: `reading_id`, `member_id`, `book_id`, `started_at` |
| Refused | `already_started` |

### `POST /api/readings/finish`

| | |
|---|---|
| Body | `reading_id`, `pages_read` (an integer, 0 or more) |
| Event | `reading_finished_v1`: `reading_id`, `member_id`, `book_id`, `started_at`, `pages_read`, `finished_at` |
| Refused | `not_started`, `finished` |

### `POST /api/clubs/plan_party`

| | |
|---|---|
| Body | `club_id` |
| Event | `party_planned_v1`: `club_id`, `parties_planned`, `planned_at` |
| Refused | `not_initiated`, `archived` |

`parties_planned` is the number of parties this club has planned so far, this one included: 1 for the first.

### `POST /api/members/unregister`

| | |
|---|---|
| Body | `member_id`, `unregistered_by` |
| Event | `member_unregistered_v1`: `member_id`, `club_id`, `name`, `registered_at`, `unregistered_by`, `unregistered_at` |
| Refused | `not_registered`, `unregistered` |

### `POST /api/books/retire`

| | |
|---|---|
| Body | `book_id`, `retired_by` |
| Event | `book_retired_v1`: `book_id`, `club_id`, `title`, `author`, `procured_at`, `club_name`, `retired_by`, `retired_at` |
| Refused | `not_procured`, `retired` |

### `POST /api/clubs/archive`

| | |
|---|---|
| Body | `club_id`, `archived_by` |
| Event | `bookclub_archived_v1`: `club_id`, `name`, `initiated_by`, `initiated_at`, `archived_by`, `archived_at` |
| Refused | `not_initiated`, `archived` |

The events that end a dossier repeat what the event that opened it said. A reader who sees only `book_retired_v1` knows the title.

## The policy

`on_member_registered_v1_maybe_plan_party`: every fifth `member_registered_v1` plans a party for the club that member joined, by sending that club a `plan_party` command.

The suite registers five members in a row in a new club and expects exactly one party from the policy. Counting per club satisfies that, and so does one counter for all clubs. A replayed event must not plan a party again.

## The four read models

| Read model | Fields | `status` is |
|---|---|---|
| clubs | `club_id`, `name`, `status`, `initiated_by`, `initiated_at` | `active`, then `archived` |
| members | `member_id`, `club_id`, `name`, `status`, `registered_at` | `active`, then `unregistered` |
| books | `book_id`, `club_id`, `title`, `author`, `status`, `procured_at` | `on_shelf`, then `retired` |
| readings | `reading_id`, `member_id`, `book_id`, `status`, `started_at`, `pages_read`, `finished_at` | `in_progress`, then `finished` |

A reading in progress has `pages_read` 0 and `finished_at` `null`.

Parties have no read model. The number of parties is told only in the answer to `plan_party`.

## The five questions

| Route | Answers |
|---|---|
| `GET /api/clubs/:club_id` | the club's row, or 404 |
| `GET /api/members/:member_id` | the member's row, or 404 |
| `GET /api/books/:book_id` | the book's row, or 404 |
| `GET /api/readings/:reading_id` | the reading's row, or 404 |
| `GET /api/members/:member_id/readings` | a JSON array of that member's reading rows, oldest `started_at` first; `[]` when there are none or the member is unknown |
