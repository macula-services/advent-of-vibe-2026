# The 24 doors

*This exists so you know, before you build, exactly what "it works" means.*

Each door is one desk of the club. The check suite knocks on each door by itself, with ids of its own, so door 13 can open while door 5 is still shut. The fields and the refusal words are in [CONTRACT.md](CONTRACT.md).

```sh
python3 open_doors/open_doors.py doors     # list them
python3 open_doors/open_doors.py run       # doors 1 to 23, and the trace for door 24
python3 open_doors/open_doors.py recheck   # door 24, after the restart
```

`run` writes a witness file, `witness.json`: which doors opened, why the others did not, and the trace that door 24 is checked against. Commit it with your evidence.

## Commands

A command door opens when the club accepts the command with the right event and version, carries every field the contract names, mints a well-formed id when none is given, and refuses what it must refuse.

| Door | Desk | Beyond the event, the club must refuse |
|---|---|---|
| 1 | `initiate_bookclub` | the same club twice (`already_initiated`); a body without a name |
| 4 | `register_member` | the same member twice (`already_registered`); a body without a name. The event carries the club's name |
| 7 | `procure_book` | the same book twice (`already_procured`); a body without a title. The event carries the club's name |
| 10 | `start_reading` | the same reading twice (`already_started`); a body without a book |
| 13 | `finish_reading` | a negative or non-numeric `pages_read`; finishing twice (`finished`); an unknown reading (`not_started`). The event repeats the start |
| 16 | `plan_party` | an unknown club (`not_initiated`). Two parties count 1, then 2, at versions 1 and 2 |
| 18 | `unregister_member` | unregistering twice (`unregistered`); an unknown member (`not_registered`) |
| 20 | `retire_book` | retiring twice (`retired`); an unknown book (`not_procured`) |
| 22 | `archive_bookclub` | archiving twice (`archived`); a party in an archived club (`archived`); an unknown club (`not_initiated`) |

## Projections

A projection door opens when, within the suite's patience, the row a reader gets shows what the event said.

| Door | Desk | The row shows |
|---|---|---|
| 2 | `bookclub_initiated` to clubs | the club, `active`, with the moment from the event |
| 5 | `member_registered` to members | the member, `active` |
| 8 | `book_procured` to books | the book, `on_shelf` |
| 11 | `reading_started` to readings | the reading, `in_progress`, 0 pages, `finished_at` null |
| 14 | `reading_finished` to readings | `finished`, the pages read, the moment it finished, the same start |
| 19 | `member_unregistered` to members | `unregistered`, the name and the registration moment kept |
| 21 | `book_retired` to books | `retired`, the title, author and procurement moment kept |
| 23 | `bookclub_archived` to clubs | `archived`, the name and the first moment kept |

## Questions

| Door | Desk | Opens when |
|---|---|---|
| 3 | `get_bookclub_by_id` | a known club is answered; an unknown one gets 404 `not_found` |
| 6 | `get_member_by_id` | the same, for a member |
| 9 | `get_book_by_id` | the same, for a book |
| 12 | `get_reading_by_id` | the same, for a reading |
| 15 | `get_readings_by_member` | a member's two readings come back oldest first, without another member's reading; an unknown member gets `[]` |

## The policy

| Door | Desk | Opens when |
|---|---|---|
| 17 | `on_member_registered_v1_maybe_plan_party` | five members registered in a row in a new club earn that club exactly one party |

The suite cannot read your event log, so it counts parties the only way the contract allows: it plans one by hand and reads `parties_planned` in the answer.

## Door 24: the log is the truth

Before the restart, the suite leaves a trace. It runs one club through its whole life: a member registers and reads a book to the end, the member leaves, the book is retired, the club is archived. It opens a second club, registers five members, and lets the policy plan their party. Then it writes down what a reader is told about each of them.

Now you restart:

1. Stop the club.
2. Delete the read model: the tables, the files, the cache, whatever your club answers questions from. Keep the event log.
3. Start the club.

`recheck` then knocks once more. The door opens when:

- every row the suite wrote down reads exactly as it did before the restart;
- the archived club still refuses a party, the open club still refuses to be initiated again, its member still cannot register twice, and the finished reading still cannot be finished again;
- the open club has exactly as many parties as before. Replaying five registrations did not plan a second party.

If you can script the restart, one run does it all:

```sh
python3 open_doors/open_doors.py run --restart-command ./restart_without_read_model.sh
```

The command must stop the club, delete the read model, start the club again and return.

A club that keeps its state in one mutable table has nothing to rebuild from and fails here. So does a club whose projections depend on the order in which two of them happen to run, and a club whose policy cannot tell a replayed event from a new one.
