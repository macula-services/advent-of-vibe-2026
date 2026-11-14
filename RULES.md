# The rules

*This exists so two rows in the table can be compared: they followed the same rules and counted cost the same way.*

## What you build

1. **The book club of the [assignment](assignment/README.md).** Nine commands, eight projections, five questions, one policy, behind the [HTTP contract](assignment/CONTRACT.md).
2. **Event sourced, with CQRS.** Every accepted command appends events to a log. The log is the only truth: the write side decides from it, and the read models are derived from it and can be thrown away. The rebuild check tests this.
3. **Vertical slices, names that scream.** One folder or file per desk, named after what the club does. No folders that sort code by technical kind (`services`, `controllers`, `models`, `handlers`, `utils` and their relatives). No event named after a row change (`created`, `updated`, `deleted`). The [stranger test](stranger_test/stranger_test.py) checks this.
4. **Working software.** The [check suite](check_bookclub/check_bookclub.py) says how many of the 23 desks pass and whether the club rebuilds its read model from the log.

## What you choose

Everything else. Each choice is a column in the table, so name it precisely.

| Column | What to write |
|---|---|
| Language | The main language of the club |
| Stack | Frameworks, the event store, the read-model store. A few words |
| Harness | The tool that drives the model: OpenCode, Claude Code, Cursor, Aider, your own loop |
| Models | Every model that produced or reviewed code, with its version |
| Add-ons | Everything else the agent was given: MCP servers, skills, rules files, templates, plugins, a corpus of conventions |

Any language is allowed, the three the table starts with included. Any library is allowed, a ready-made event store included. Any input to the agent is allowed, the three reference clubs included, as long as your entry names it.

## Where it lives

In a public repository that you choose and control. The entry names one commit of it. Every number in your row is about that commit. Any licence, or none.

## How cost is counted

Cost is the hard part to compare, so the rules are strict here.

1. **The meter runs from the first prompt to the entered commit.** Everything the agent consumed on the way counts: planning, dead ends, retries, reviews by a second model, the runs that fixed the last failing desk.
2. **Started over? Count it all.** If you threw an attempt away and began again, the thrown-away attempts are part of the cost. `attempts` says how many there were.
3. **Report the basis.**
   - `billed`: what the provider charged, from its usage export.
   - `list-price`: you pay a flat subscription, so you report the tokens used at the provider's public per-token price on the day.
   - `local`: the model ran on your own hardware. The cost is 0, and your notes name the hardware and how long it ran.
4. **Report the tokens.** Input plus output, all models added up. Tokens are the number that stays comparable when prices change.
5. **Count the human.** `human_turns` is the number of messages you typed to the agent. `hand_written_lines` is the number of lines in the entered commit that a person typed. Editing by hand is allowed. Hiding it is not.
6. **Count the clock.** `agent_minutes` is the time the agent spent working, not the time you spent waiting to start it.

What does not count: your own time, your editor, the electricity, and the cost of writing the entry file.

## The evidence

Your repository carries a folder, `vibe/` unless your entry says otherwise, with:

- the witness file the check suite wrote (`witness.json`);
- the provider's usage or cost export, or a screenshot of it, with keys and account numbers removed;
- the first prompt you gave the agent, word for word (`FIRST_PROMPT.md`);
- what the agent was given or read: rules files, skills, templates, repositories (`INPUTS.md`);
- the entry file as the agent filled it (`entry.toml`).

An agent that follows [AGENTS.md](AGENTS.md) leaves all of these behind except the cost export.

The evidence is what lets a stranger believe your row. Never commit a secret to it.

## How an entry is checked

By anyone. The repository is public, the suite is one command, and the commit is named. A row that cannot be reproduced gets an issue in this repository, and an entry whose owner does not answer within two weeks is marked in its notes.

The suite cannot see whether you really deleted the read model before the rebuild check, or whether your cost export is complete. It does not have to. Your repository is public and your name is on the row.

## Dates

- **1 December 2026.** The assignment and the suite are frozen as version 1.0.0. Until then they may still change, and entries are welcome as trial runs.
- **6 January 2027.** The table is tagged `results-2026`. That tag is the result of this edition.
- **After that.** Entries stay open. The table keeps growing; the tag does not move.

A row checked with an older suite stays in the table, and its suite version is shown beside it.

## Conduct

The [code of conduct](CODE_OF_CONDUCT.md) applies to issues, pull requests and reviews of other people's entries. Doubt a row by reproducing it, and say what you found.
