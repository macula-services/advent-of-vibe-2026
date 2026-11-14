# Advent of Vibe 2026

*This exists so anyone can find out, in public, what it costs an AI agent to build the same small system in the language of their choice.*

An AI agent built a book club in Erlang for about two dollars. The same club in Elixir cost about five. In Gleam it cost about seventeen. Same design, same harness, same model: [OpenCode](https://opencode.ai) with DeepSeek v4.

Why the difference? The language? The libraries? The model's training? Luck? Three rows cannot say. A hundred rows can.

## The challenge

Build the same book club, in any language you like, with an AI agent doing the building. Then tell everyone what it cost.

You choose the language, the stack, the harness, the model or models, and any add-ons. Each of those is a column in [the table](TABLE.md). Three things are fixed:

1. **It is event sourced, with CQRS.** The log of events is the truth. Everything a reader sees is derived from it.
2. **It is sliced vertically and its names scream.** One folder per thing the club can do. A stranger reads what the system does from the folder names alone.
3. **It works.** A check suite knocks on 24 doors over HTTP. Your club opens them or it does not.

Your club lives in a public repository that you choose and control. Your result is public. Using the Macula mesh is optional.

There is no jury and no prize. There is a table, and every row in it can be checked by anyone with one command.

## The 24 doors

An advent calendar has 24 doors. So does the book club: one door per desk, in the order you would build them. A desk is one thing the club can do, one event written down, or one question answered.

| Door | Desk | Kind |
|---|---|---|
| 1 | `initiate_bookclub` | command |
| 2 | `bookclub_initiated` to clubs | projection |
| 3 | `get_bookclub_by_id` | question |
| 4 | `register_member` | command |
| 5 | `member_registered` to members | projection |
| 6 | `get_member_by_id` | question |
| 7 | `procure_book` | command |
| 8 | `book_procured` to books | projection |
| 9 | `get_book_by_id` | question |
| 10 | `start_reading` | command |
| 11 | `reading_started` to readings | projection |
| 12 | `get_reading_by_id` | question |
| 13 | `finish_reading` | command |
| 14 | `reading_finished` to readings | projection |
| 15 | `get_readings_by_member` | question |
| 16 | `plan_party` | command |
| 17 | on member registered, maybe plan party | policy |
| 18 | `unregister_member` | command |
| 19 | `member_unregistered` to members | projection |
| 20 | `retire_book` | command |
| 21 | `book_retired` to books | projection |
| 22 | `archive_bookclub` | command |
| 23 | `bookclub_archived` to clubs | projection |
| 24 | the log is the truth | restart |

Door 24 is the one that tells an event-sourced system from one that only looks like it. Stop the club. Throw its read model away. Start it again. Every answer is back, the club still refuses what it refused before, and nothing happened twice.

## Taking part

1. Read the [assignment](assignment/README.md): the club on one wall of sticky notes, the [24 doors](assignment/DOORS.md) and the [HTTP contract](assignment/CONTRACT.md).
2. Read the [rules](RULES.md), above all how cost is counted, before your agent writes its first line.
3. Let your agent build the club in your own public repository.
4. Check it:

   ```sh
   python3 open_doors/open_doors.py run --base-url http://127.0.0.1:8488
   # stop your club, delete its read model, start it again
   python3 open_doors/open_doors.py recheck --base-url http://127.0.0.1:8488
   python3 stranger_test/stranger_test.py path/to/your/checkout
   ```

5. Add your row: one file in `entries/`, by pull request. [CONTRIBUTING.md](CONTRIBUTING.md) walks you through it.

An unfinished club is a welcome entry. Fourteen doors for forty cents is a result too.

## What is in this repository

| Folder | What it holds |
|---|---|
| [`assignment/`](assignment/README.md) | The book club: the wall, the doors, the HTTP contract, the optional mesh track |
| [`open_doors/`](open_doors/) | The check suite: one command against a running club |
| [`stranger_test/`](stranger_test/) | The structure check: reads the folder and file names of a checkout |
| [`entries/`](entries/) | One file per entry, and the template to copy |
| [`draw_table/`](draw_table/) | Draws [TABLE.md](TABLE.md) from the entries |

All three tools are plain Python 3.11 or newer, standard library only. Nothing to install.

## Why a book club

It is small enough to hold in your head and large enough to go wrong in every way that matters. It has four things with a life of their own (a club, a member, a book, a reading), each with a beginning and an end. It has a rule that reaches from one to another (every fifth member earns the club a party). It has four read models and five questions. An agent that gets this right has shown it can do event sourcing, CQRS and vertical slicing, not only talk about them.

The three clubs the table starts with are public: [Erlang](https://github.com/macula-services/mcl-bookclub), [Elixir](https://github.com/macula-services/mcl-bookclub-phoenix), [Gleam](https://github.com/macula-services/mcl-bookclub-gleam). You may read them, and so may your agent, as long as your entry says so.

## Licence

Apache-2.0. The wall picture comes from [mcl-corpus](https://github.com/macula-services/mcl-corpus) (MIT).

Advent of Vibe is not affiliated with Advent of Code.
