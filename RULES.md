# The rules

*This exists so two rows of the datasheet can be compared: they built the same thing and counted cost the same way.*

There are five.

1. **Event sourced, with CQRS.** Every accepted command appends events to a log. The log is the only truth: the write side decides from it, and the read models are derived from it and can be thrown away. The rebuild check tests this.
2. **The observer too.** The club tells the outside world three facts. A second service, the observer, sees only those facts, keeps a read model of its own and answers one question: the scoreboard. You build both, as the [assignment](assignment/README.md) describes them. How the facts travel from the club to the observer is yours to choose.
3. **Vertical slices, names that scream.** One folder or file per desk, named after what it does. No folders that sort code by technical kind (`services`, `controllers`, `models`, `handlers`, `utils` and their relatives). No event named after a row change (`created`, `updated`, `deleted`). The [stranger test](stranger_test/stranger_test.py) checks this.
4. **Your language, your supporting services.** The language, the stack, the database, the broker, the harness, the models: all yours to choose. Use anything that helps you reach the goal.
5. **One command starts it.** Your repository carries a compose file, or another mechanism of your choosing, that starts the club, the observer and whatever they need. Your entry names the command.

That is all. The rest of this page says what the columns of the [datasheet](DATASHEET.csv) mean.

## What is measured

- **Desks.** The [check suite](check_bookclub/check_bookclub.py) talks to your running club and observer over [HTTP](assignment/CONTRACT.md) and says how many of the 27 desks pass.
- **Rebuilds.** The suite says whether the club rebuilds its read model from the log.
- **Stranger test.** Pass or fail.
- **Cost.** What it took the agent to get there.

An unfinished club is a valid entry. Its row says how far it got.

## Your formula

Each choice is a column, so that formulas can be compared. Name each one precisely, and the way others would name it: `PostgreSQL`, not `my database`.

| Column | What to write |
|---|---|
| `language` | The main language of the club |
| `frameworks` | The frameworks and libraries that shape the code. A few words |
| `event_store` | What keeps the event log: a product, or "my own, in" a database |
| `read_model_store` | What keeps the read models |
| `fact_carrier` | What carries the three facts from the club to the observer: a broker, the Macula mesh, a webhook |
| `other_services` | Anything else that must run for the solution to work |
| `harness` | The tool that drives the model: OpenCode, Claude Code, Cursor, Aider, your own loop |
| `models` | Every model that produced or reviewed code, with its version |
| `provider` | Who served the models: the vendor, a reseller, or `self` for your own machine |
| `addons` | Everything else the agent was given: MCP servers, skills, rules files, templates, plugins, a corpus of conventions, the reference clubs |
| `runs_on` | Where the models ran: `hosted`, `local` or `both` |
| `hardware` | The machine the work ran on. For a local model, its GPU too |
| `run_with` | The one command that starts the club and its observer |

More columns may come as more formulas arrive. A new column never makes an old row wrong: the old row is empty there.

## One row per run

A row is one run of one formula. Run it again and you have a second row, with its own repository commit and its own cost. Several runs of the same formula are welcome: they show how much of a number is luck.

## Where it lives

In a public repository that you choose and control. The entry names one commit of it, and every number in your row is about that commit. Any licence, or none. Your row is public, and so is the whole datasheet.

## How cost is counted

| Field | What it counts |
|---|---|
| `usd` | Everything the agent consumed from the first prompt to the entered commit: planning, dead ends, retries, reviews by a second model. Attempts you threw away count too |
| `basis` | `billed`: what the provider charged. `list-price`: you pay a flat subscription and report the tokens at the provider's public price. `local`: the model ran on your own hardware, the cost is 0 and your notes name the hardware |
| `tokens` | Input plus output, all models added up |
| `agent_minutes` | The time the agent spent working |
| `human_turns` | The messages you typed to the agent |
| `hand_written_lines` | The lines of the entered commit that a person typed |
| `attempts` | How many times you started over, the last one included |

Your own time, your editor and the electricity do not count.

## The evidence

Your repository carries a folder, `vibe/` unless your entry says otherwise, with:

- the witness file the check suite wrote (`witness.json`);
- the provider's usage or cost export, or a screenshot of it, with keys and account numbers removed;
- the first prompt you gave the agent, word for word (`FIRST_PROMPT.md`);
- what the agent was given or read (`INPUTS.md`);
- the entry file as the agent filled it (`entry.toml`).

An agent that follows [AGENTS.md](AGENTS.md) leaves all of these behind except the cost export. Never commit a secret to it.

## How a row is checked

By anyone. The repository is public, the commit is named, one command starts the solution and one command checks it. If your result differs from a row, open an issue here that says what you ran and what you saw.

A row checked with an older suite stays in the table, and its suite version is shown beside it.

## Conduct

The [code of conduct](CODE_OF_CONDUCT.md) applies to issues, pull requests and reviews of other people's entries. Doubt a row by reproducing it, and say what you found.
