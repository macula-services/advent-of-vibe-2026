# The mesh track (optional)

*This exists so a club can tell other systems what happened in it, without those systems reading its event log.*

A club's events are its own business. Three of them matter to the outside world, so the club publishes each of those as a **fact**: a message with a fixed public shape, on a named topic of the [Macula mesh](https://github.com/macula-io/macula). The pink notes on the wall are these three facts.

Taking this track sets the `mesh` column of your row to yes. It adds no check, and a club without it is a complete entry.

## The three facts

| When the club records | It publishes the fact | With these fields |
|---|---|---|
| `member_registered_v1` | `member_registered`, version 1 | `member_id`, `club_id`, `club_name`, `name`, `registered_at` |
| `book_procured_v1` | `book_procured`, version 1 | `book_id`, `club_id`, `club_name`, `title`, `author`, `procured_at` |
| `book_retired_v1` | `book_retired`, version 1 | `book_id`, `club_id`, `club_name`, `title`, `author`, `procured_at`, `retired_by`, `retired_at` |

The Erlang club publishes them on these topics in the `io.macula` realm:

```
io.macula/mcl-bookclub/bookclub/member/member_registered_v1
io.macula/mcl-bookclub/bookclub/book/book_procured_v1
io.macula/mcl-bookclub/bookclub/book/book_retired_v1
```

Your club publishes under its own name in place of `mcl-bookclub`.

## The rules of a fact

- A fact is not the event. It is a separate message with its own shape, chosen for readers outside the club. Each fact carries the club's name as well as its id, so a reader needs nothing else to understand it.
- One emitter per fact, in a folder named after it: `emit_member_registered_v1_to_mesh`.
- A published fact never changes shape. If the club has more to say, it publishes version 2 beside version 1.
- No booleans on the wire: true and false travel as 1 and 0.
- Publishing a fact is not replayed. A club that restarts does not tell the world again what it already told.

## What you need

A Macula SDK for your language, a realm to publish in, and a station to connect to. SDKs exist for [Erlang and Elixir](https://github.com/macula-io/macula), [Go](https://github.com/macula-io/macula-go), [TypeScript](https://github.com/macula-io/macula-ts), [Python](https://github.com/macula-io/macula-py), [.NET](https://github.com/macula-io/macula-dotnet), [Rust](https://github.com/macula-io/macula-rust) and [PHP](https://github.com/macula-io/macula-php). [macula-ecosystem](https://github.com/macula-io/macula-ecosystem) explains how to join a realm.

The Erlang club's emitters and its fact shapes are in [`mcl-bookclub`](https://github.com/macula-services/mcl-bookclub/tree/main/apps/host_bookclub/src), in the three `emit_*_to_mesh` folders and in `mcl_bookclub_facts.erl`.
