# The table

<!-- Drawn by draw_table/draw_table.py from entries/. Do not edit by hand. -->

Every row is one run: an AI agent building the book club and its observer with one formula, the language, the services, the harness and the models of that row. A run is complete when all 27 desks pass, the club rebuilds its read model from the log, and the stranger test passes; complete runs are ranked by cost, cheapest first.

This page shows the columns a reader compares first. Every column of every run is in [DATASHEET.csv](DATASHEET.csv): load it into a spreadsheet and sort it your own way. [RULES.md](RULES.md) says what each column means.

## Runs

No runs yet. The first row is yours: [CONTRIBUTING.md](CONTRIBUTING.md) says how.

## The three that started it

Three clubs were built before the rules existed. Their cost is what their author remembers, and most of what the rules ask for was never recorded. They are here as the first three measurements, not as runs under the rules.

| # | Language | Frameworks | Event store | Read models | Facts travel by | Harness | Models | Runs on | Cost | Tokens | Desks | Rebuilds | Repository |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|  | Erlang | OTP 28, evoq, cowboy | reckon_db | sqlite | Macula mesh | OpenCode | DeepSeek v4 | hosted | ~$2.00 | not recorded | 22 of 27 | no | [macula-services/mcl-bookclub](https://github.com/macula-services/mcl-bookclub) |
|  | Elixir | Phoenix LiveView, evoq | reckon_db | sqlite | Macula mesh | OpenCode | DeepSeek v4 | hosted | ~$5.00 | not recorded | not run | not run | [macula-services/mcl-bookclub-phoenix](https://github.com/macula-services/mcl-bookclub-phoenix) |
|  | Gleam | OTP 28, evoq, cowboy | reckon_db | sqlite | Macula mesh | OpenCode | DeepSeek v4 | hosted | ~$17.00 | not recorded | not run | not run | [macula-services/mcl-bookclub-gleam](https://github.com/macula-services/mcl-bookclub-gleam) |
