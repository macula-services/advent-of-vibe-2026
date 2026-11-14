# For the coding agent

*This exists so one sentence from a person is enough: "check macula-services/advent-of-vibe-2026 and macula-services/mcl-bookclub, and build a clone in language X from it."*

You were pointed here to build a book club. This page is your whole brief. Follow it top to bottom and you will not need to ask the person anything except what is listed under "Ask once".

## The job

Build the book club of this repository's assignment, in the language the person named, in a new repository of their own. It must be event sourced with CQRS, sliced vertically with names that say what the club does, and it must pass the check suite in this repository.

## Read these, in this order

1. [`assignment/README.md`](assignment/README.md): what the club is, as a wall, a table and a folder tree.
2. [`assignment/CONTRACT.md`](assignment/CONTRACT.md): every route, field and refusal word. This is the specification.
3. [`assignment/CHECKS.md`](assignment/CHECKS.md): what the suite checks, desk by desk, and the rebuild check.
4. [`RULES.md`](RULES.md): what is fixed, and what the person must be able to report afterwards.

Then read the reference club, [`macula-services/mcl-bookclub`](https://github.com/macula-services/mcl-bookclub), for its shape:

| Folder there | What to take from it |
|---|---|
| `apps/host_bookclub/src/` | One folder per command, with the command, its event, the rule that decides and its entry point. The four aggregates. The policy folder `on_member_registered_v1_maybe_plan_party/` |
| `apps/project_bookclub/src/` | One folder per event, each writing one read-model table |
| `apps/query_bookclub/src/` | One folder per question |
| `apps/mcl_bookclub/src/mcl_bookclub_admin.erl` | The HTTP routes |

**Where the reference and the contract disagree, the contract wins.** The reference has known defects that you must not copy:

- Its projections overwrite a row without comparing versions, so a rebuilt read model can show an ended dossier as active. Write each row only when the event is newer than what the row holds, or project each stream in order.
- It answers `finished_at` as the string `"undefined"` for a reading in progress. The contract says `null`.
- It turns unknown JSON keys from a caller into interned atoms. Ignore unknown keys without keeping them.

**Do not clone what is not the club.** Leave out the reference's mesh facade, its `emit_*_to_mesh` folders, its health endpoint, its admin web page, its container files, its release scripts and its architecture diagrams. The mesh track is optional and only for a person who asks for it ([`assignment/MESH.md`](assignment/MESH.md)).

## Ask once

Before you write code, ask the person only for what you cannot know, in one message:

- the name and location of the new repository, if they have not said;
- whether they want the optional mesh track (default: no).

Do not ask about the stack. Choose one that is ordinary for the language, and say what you chose.

## Build

1. Keep the three departments apart: one place that decides (commands, aggregates, the policy), one that records (projections), one that answers (queries). Three packages, modules or folders, as the language prefers.
2. One folder or file per desk, named after the desk in the language's own spelling: `register_member`, `RegisterMember`, `register-member`. No folder named after a technical kind (`services`, `controllers`, `models`, `handlers`, `utils`, `commands`, `events`, `queries` and their relatives). No name with `created`, `updated` or `deleted`.
3. Keep an append-only event log that survives a restart. Decide every command from the events of its own stream. Derive every read model from the log, and keep the read model somewhere that can be deleted without touching the log.
4. The policy reacts to new events only. An event that is replayed after a restart must not plan a party.
5. Serve the contract on `http://127.0.0.1:8488`, or on another port that you then pass to the suite.
6. Build desk by desk, in the order of [`assignment/CHECKS.md`](assignment/CHECKS.md), and run the suite as you go. Each desk is checked by itself, so the count rises as you work.
7. Write `restart_without_read_model.sh` in the new repository: it stops the club, deletes the read model and nothing else, starts the club again and returns.
8. Write tests of your own for the rules of the four dossiers. The suite is a check from outside, not a replacement for them.

## Check

Clone this repository next to the new one and run its tools from there. They need Python 3.11 or newer and nothing else. Do not change them.

```sh
python3 check_bookclub/check_bookclub.py run \
    --base-url http://127.0.0.1:8488 \
    --witness <new repository>/vibe/witness.json \
    --restart-command <new repository>/restart_without_read_model.sh
python3 stranger_test/stranger_test.py <new repository>
```

You are done when the first prints `desks: 23 of 23, rebuilds from the log: yes` and the second prints `stranger test: pass`. If you cannot get there, stop and report the count you reached and what blocks the rest: an unfinished club is a valid entry.

## Leave the evidence

In the new repository, in a folder named `vibe/`:

- `witness.json`, written by the suite.
- `FIRST_PROMPT.md`: the person's first message to you, word for word.
- `INPUTS.md`: everything you were given or read to do the job: this repository, the reference club, rules files, skills, MCP servers, templates.
- `entry.toml`: a copy of [`entries/TEMPLATE.toml`](entries/TEMPLATE.toml), filled in. Fill in what you know for certain: the repository, the language, the stack, the harness and the models if you know them, the desks, the rebuild result, the suite version (`check_bookclub.py --version`), the stranger test result. List this repository and the reference club under `addons`.
- If your harness can show the tokens and the cost of this session, save its output as `vibe/cost.txt` and use those numbers.

Never write a secret, a key or an account number into `vibe/`.

## Tell the person what is left for them

End with one short message that says:

- the result: desks, rebuild, stranger test;
- the stack you chose;
- which fields of `vibe/entry.toml` you could not fill and they must: usually `usd`, `basis`, `tokens`, `agent_minutes`, `human_turns`, `hand_written_lines`, `attempts`, and `commit` once they have pushed;
- that the repository must be public, and that the row is added by a pull request to this repository with `vibe/entry.toml` copied to `entries/<handle>-<language>.toml` and the table redrawn (`python3 draw_table/draw_table.py`). Open that pull request yourself only if they ask.
