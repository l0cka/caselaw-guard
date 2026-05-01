# openbench

Open Australian case-law citation lookup API.

> **openbench is not an official court or government API. openbench does not provide legal advice. Results reflect only the configured open index — absence of a citation is not proof a case does not exist. Always verify important matters against authorised sources (court websites, AustLII, JADE).**

openbench resolves Australian neutral citations (e.g. `[1992] HCA 23`) against an index built from the [Open Australian Legal Corpus](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus) by Isaacus, and returns structured metadata with explicit provenance.

## Quickstart

```bash
git clone https://github.com/danielkurdi/openbench
cd openbench
uv sync --extra dev
uv run openbench serve --index data/fixtures/index.json
```

In another terminal:

```bash
curl "http://127.0.0.1:8000/v1/au/citations/%5B1992%5D%20HCA%2023" | jq
```

You should see a `verified` response for *Mabo v Queensland (No 2)*.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness + `index_loaded` flag |
| `GET /v1/au/citations/{citation}` | Resolve a single citation |
| `GET /v1/au/index/metadata` | Index version, source, attribution |
| `GET /v1/au/index/stats` | Record counts by court, year, ambiguity |

Statuses: `verified`, `not_found`, `ambiguous`, `unsupported_format`, `index_unavailable`. Full reference: [`docs/api.md`](docs/api.md).

## Building your own index

Download the Isaacus corpus, transform to JSONL with the fields openbench expects, then:

```bash
uv run openbench index build path/to/corpus.jsonl --output index.json
AUS_CASE_INDEX=$(pwd)/index.json uv run openbench serve --index $(pwd)/index.json
```

See [`docs/self-hosting.md`](docs/self-hosting.md) for the full process.

## Licensing & attribution

- Code: Apache-2.0 (see `LICENSE`).
- Index data (`data/fixtures/index.json` and any released `index-*.json` artifact): CC-BY-4.0, derived from the Open Australian Legal Corpus by Isaacus. See `LICENSE-DATA` and `DATA_SOURCES.md`.

  > Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction, normalisation, deduplication).

## Status

v1: local MVP. No public hosted API yet. See `docs/superpowers/specs/2026-05-01-openbench-design.md` for scope.
