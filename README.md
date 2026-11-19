# OpenCapacity

OpenCapacity is a proposed open API for data center capacity. A customer describes the capacity it
needs as a requirement and uses it in three ways:

- Query: ask a provider whether the requirement can be met. The provider returns a graded answer.
- Signal: record the requirement with the provider as a standing need. The customer can amend,
  withdraw, or delete it.
- Subscription: receive an event when the answer to the requirement changes.

Status: draft, version 1.0.0-draft.1. No provider implements this API. It is an independent
proposal by Ian Jones. It is not a product or a commitment of any data center provider, and it
contains no provider's capacity, customer, or internal data. Every example uses invented names
and values.

## Graded answers

Every answer element is one of four grades:

| Grade | Meaning |
| --- | --- |
| `AVAILABLE` | The requirement is met, or will be met by the date it is needed for service. |
| `POSSIBLE` | It can be met with conditions, or the provider has to review it. |
| `UNAVAILABLE` | It is not met and will not be met by the date it is needed for service. |
| `NOT_DISCLOSED` | The provider does not answer this through the API. |

Density, cabinet count, power, and dates come back as ranges, and each range is optional. A
provider that returns only a grade per location conforms. An answer is an indication. It is not an
offer, a quote, or a reservation, and it expires.

## What is in this repository

| Path | Contents |
| --- | --- |
| `opencapacity-1.0.yaml` | The OpenAPI 3.1 document. It is the source of truth. |
| `opencapacity-1.0.json` | The same document as JSON, generated from the YAML. |
| `tools/examples.py` | Generates most of the examples and all of `x-exchanges` in the document. |
| `tools/check.sh` | Regenerates the examples and JSON, and checks the document. |
| `reference-provider/` | An in-memory provider with synthetic data, for testing a client. |

The document has 64 named examples. `x-exchanges` arranges them into complete request and response
exchanges in the order of real use: discovery, queries, errors, the life of a signal, webhook
subscriptions, and reading or streaming events.

## Read the specification

Open `opencapacity-1.0.yaml` in any OpenAPI viewer. The narrative, the reference tables, and the
worked examples are at https://eqixiac.com/opencapacity/overview.

## Check the specification

`tools/check.sh` needs `python3`, a JDK 21 or later, and the Jackson YAML library in your local
Maven repository. The script names the command that fetches the library.

```sh
tools/check.sh
```

It confirms that every reference resolves, that every example validates against the schema of the
operation and status it is used with, that every example is used in an exchange, that the worked
webhook signature verifies, and that deliberately invalid payloads are rejected.

## Run the reference provider

The reference provider serves the whole API on a local port from an invented inventory of three
metros and four facilities. It needs JDK 21 or later and Maven.

```sh
mvn -f reference-provider/pom.xml verify
```

Start it from a test with `ReferenceProvider.start()`, and give `endpoint()` to your client. The
client ID and secret are the constants `CLIENT_ID` and `CLIENT_SECRET`. Use `disclosure(...)` to
switch between the three disclosure profiles: grade only, banded, and full.

The reference provider keeps nothing on disk and is not for production use. It is not a
conformance suite.

## Comment on the proposal

Open an issue in this repository.

## License

Apache License 2.0. See `LICENSE`.
