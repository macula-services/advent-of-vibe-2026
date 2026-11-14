# Advent of Vibe 2026

*This exists so anyone can find out, in public, what it costs an AI agent to build the same small system in the language of their choice.*

An AI agent built a book club in Erlang for about two dollars. The same club in Elixir cost about five. In Gleam it cost about seventeen. Same design, same harness, same model: [OpenCode](https://opencode.ai) with DeepSeek v4.

Why the difference? The language? The libraries? The model's training? Luck? Three rows cannot say. A hundred rows can.

## The challenge

Build the same book club, in any language you like, with an AI agent doing the building. Then tell everyone what it cost.

There are five rules:

1. **It is event sourced, with CQRS.** The log of events is the truth. Everything a reader sees is derived from it.
2. **It has an observer.** The club tells the outside world three facts. A second service sees only those facts and keeps a scoreboard from them. You build both.
3. **It is sliced vertically and its names scream.** One folder per thing the system can do. A stranger reads what it does from the folder names alone.
4. **The language and the supporting services are yours.** So are the harness, the models and anything else that helps. Each choice is a column in [the table](TABLE.md).
5. **One command starts it.** A compose file, or another mechanism of your choosing.

Your club lives in a public repository that you choose and control. Your result is public. [RULES.md](RULES.md) has the rules in full.

There is no jury and no prize. There is a table, and every row in it can be checked by anyone with one command.

## What gets checked

A check suite talks to your running club and observer over HTTP. It checks 27 desks: 23 belong to the club and 4 to the observer. A desk is one thing the system can do, one event written down for readers, or one question answered. The suite checks each desk by itself, so a half-built club still gets a count.

| | Desk | Kind |
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
| 24 | `ingest_member_registered` | observer |
| 25 | `ingest_book_procured` | observer |
| 26 | `ingest_book_retired` | observer |
| 27 | `get_scoreboard` | observer |

Then comes the check that tells an event-sourced system from one that only looks like it. Stop the club. Throw its read model away. Start it again. Every answer is back, the club still refuses what it refused before, and nothing happened twice. The table calls this **rebuilds**: yes or no.

## Taking part

Tell your coding agent one sentence:

> Check macula-services/advent-of-vibe-2026 and macula-services/mcl-bookclub, and build a clone of the book club in Rust from it.

Put your own language where it says Rust. That sentence is the whole brief: [AGENTS.md](AGENTS.md) tells the agent what to read, what to build, how to check its own work, and what evidence to leave behind.

When the agent is done, three things are left for you:

1. Make the repository public.
2. Fill in what only you know in `vibe/entry.toml`: what it cost, how many tokens, how often you had to step in. [RULES.md](RULES.md) says how cost is counted.
3. Add your row: copy that file into `entries/` here, by pull request. [CONTRIBUTING.md](CONTRIBUTING.md) walks you through it.

You can check a club yourself at any time:

```sh
python3 check_bookclub/check_bookclub.py run --base-url http://127.0.0.1:8488 --observer-url http://127.0.0.1:8489
# stop your club, delete its read model, start it again
python3 check_bookclub/check_bookclub.py recheck --base-url http://127.0.0.1:8488
python3 stranger_test/stranger_test.py path/to/your/checkout
```

An unfinished club is a welcome entry. Fourteen desks for forty cents is a result too.

## What is in this repository

| Folder | What it holds |
|---|---|
| [`AGENTS.md`](AGENTS.md) | The brief for the coding agent: one sentence from you is enough |
| [`assignment/`](assignment/README.md) | The book club and its observer: the wall, what is checked, the HTTP contract, the three facts |
| [`check_bookclub/`](check_bookclub/) | The check suite: one command against a running club and observer |
| [`stranger_test/`](stranger_test/) | The structure check: reads the folder and file names of a checkout |
| [`entries/`](entries/) | One file per entry, and the template to copy |
| [`draw_table/`](draw_table/) | Draws [TABLE.md](TABLE.md) from the entries |

All three tools are plain Python 3.11 or newer, standard library only. Nothing to install.

## Why a book club

It is small enough to hold in your head and large enough to go wrong in every way that matters. It has four things with a life of their own (a club, a member, a book, a reading), each with a beginning and an end. It has a rule that reaches from one to another (every fifth member earns the club a party). It has four read models and five questions. An agent that gets this right has shown it can do event sourcing, CQRS and vertical slicing, not only talk about them.

The three clubs the table starts with are public: [Erlang](https://github.com/macula-services/mcl-bookclub), [Elixir](https://github.com/macula-services/mcl-bookclub-phoenix), [Gleam](https://github.com/macula-services/mcl-bookclub-gleam). The Erlang club's observer is [mcl-bookclub-observer](https://github.com/macula-services/mcl-bookclub-observer). Read them, and let your agent read them.

## Licence

Apache-2.0. The wall picture comes from [mcl-corpus](https://github.com/macula-services/mcl-corpus) (MIT).

Advent of Vibe is not affiliated with Advent of Code.
