# Carrying the facts over the mesh

*This exists so a club that wants to tell the whole world what happened in it, and not only its own observer, knows one way to do it.*

The three facts and their fields are part of the [contract](CONTRACT.md#the-three-facts): every club publishes them, and every observer lives on them. How they travel is yours to choose. A message broker, a webhook, a shared log: anything that gets a fact from the club to the observer will do.

The reference club carries them over the [Macula mesh](https://github.com/macula-io/macula). On the mesh a fact is a message on a named topic, and any system in the realm can listen, not only the observer you built. This page says how the reference does it, for those who want the same.

Carrying the facts over the mesh sets the `mesh` column of your row to yes. It adds no check, and it is not needed for a complete entry.

## The topics

The Erlang club publishes on these topics in the `io.macula` realm:

```
io.macula/mcl-bookclub/bookclub/member/member_registered_v1
io.macula/mcl-bookclub/bookclub/book/book_procured_v1
io.macula/mcl-bookclub/bookclub/book/book_retired_v1
```

Your club publishes under its own name in place of `mcl-bookclub`.

## What the mesh asks of a fact

- No booleans on the wire: true and false travel as 1 and 0.
- A published fact never changes shape. If the club has more to say, it publishes version 2 beside version 1.

## What you need

A Macula SDK for your language, a realm to publish in, and a station to connect to. SDKs exist for [Erlang and Elixir](https://github.com/macula-io/macula), [Go](https://github.com/macula-io/macula-go), [TypeScript](https://github.com/macula-io/macula-ts), [Python](https://github.com/macula-io/macula-py), [.NET](https://github.com/macula-io/macula-dotnet), [Rust](https://github.com/macula-io/macula-rust) and [PHP](https://github.com/macula-io/macula-php). [macula-ecosystem](https://github.com/macula-io/macula-ecosystem) explains how to join a realm.

The Erlang club's emitters and its fact shapes are in [`mcl-bookclub`](https://github.com/macula-services/mcl-bookclub/tree/main/apps/host_bookclub/src), in the three `emit_*_to_mesh` folders and in `mcl_bookclub_facts.erl`. The observer that listens to them is [`mcl-bookclub-observer`](https://github.com/macula-services/mcl-bookclub-observer).
