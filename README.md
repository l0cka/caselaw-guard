# CaseLaw Guard

CaseLaw Guard is an Apache-2.0 verifier for agents and drafting workflows that need to fail closed on fabricated case-law citations. Australian citation-index support is built into the package and works offline with a local index.

The v0 guarantee is deliberately narrow: **citation existence only**. It does not decide whether a case supports a legal proposition, whether a case remains good law, or whether any output is legal advice.

## What It Does

- Extracts case-law citations locally from plain text or Markdown.
- Verifies citations through configured legal-source adapters.
- Sends only citation strings or citation components to external providers by default.
- Returns stable JSON that agents can use to block, retry, or show unresolved citations.
- Exits non-zero from the CLI when any extracted citation is not verified.

## Install

For the command-line verifier:

```bash
python3 -m pip install caselaw-guard
```

For local agent or MCP use:

```bash
python3 -m pip install "caselaw-guard[mcp]==0.3.0"
```

## Australian five-minute setup

Install the package, fetch an explicit verified index release, and verify a
citation offline:

```bash
python3 -m pip install "caselaw-guard[mcp]==0.3.0"
caselaw-guard au-index fetch 2026-08-01 --output australia-index.json
printf '[2014] HCA 9 at [10]\n' \
  | caselaw-guard verify - --no-courtlistener --au-index australia-index.json
caselaw-guard-mcp
```

`au-index fetch` accepts only an explicit `YYYY-MM-DD` release version. It
downloads the compressed index and checksum manifest from this repository,
streams and verifies both assets, validates the canonical provenance, and
replaces the output atomically. Checksums protect asset integrity in transit;
they do not protect against a compromised repository or release account.

The approved full-index coverage report for `australian-index-2026-08-01` is
the [AusLaw citation coverage report](benchmarks/reports/australian-index-2026-08-01.json).
It measures extraction and existence in one dated index snapshot, not legal
proposition support, good-law status or ongoing source completeness.

## Quickstart

Verify a draft after setting up a provider:

```bash
caselaw-guard verify draft.md
```

CaseLaw Guard fails closed. If no configured provider supports an extracted citation, the result is not treated as verified.

Most users need one provider setup:

| Citation source | Setup |
| --- | --- |
| U.S. case citations | Set `CASELAW_GUARD_COURTLISTENER_TOKEN` or pass `--courtlistener-token`. |
| Australian neutral citations | Pass `--au-index /path/to/australia-index.json` or set `CASELAW_GUARD_AU_INDEX`. |
| Local agents over MCP | Install `caselaw-guard[mcp]`, then run `caselaw-guard-mcp`. |

For a no-network smoke test, verify Australian neutral citations from stdin using a local index:

```bash
printf 'Mabo v Queensland (No 2) [1992] HCA 23\n' \
  | caselaw-guard verify - --no-courtlistener --au-index examples/australia_index.sample.json
```

The CLI exits `0` only when every extracted citation is `verified`; otherwise it exits `1`.

## CLI

Verify a Markdown or text draft with explicit providers:

```bash
caselaw-guard verify draft.md \
  --courtlistener-token "$CASELAW_GUARD_COURTLISTENER_TOKEN" \
  --au-index examples/australia_index.sample.json
```

Use an opt-in CourtListener cache when repeated checks are expected:

```bash
caselaw-guard verify draft.md \
  --courtlistener-token "$CASELAW_GUARD_COURTLISTENER_TOKEN" \
  --cache .cache/courtlistener.json \
  --cache-ttl-days 30
```

The cache stores citation lookup inputs and provider results only. It does not store source document text, and provider errors or rate-limit responses are not cached.

Build a compact Australian citation index from a local Open Australian Legal Corpus `corpus.jsonl`:

```bash
caselaw-guard au-index build ~/Downloads/corpus.jsonl \
  --output data/australia-index.json \
  --index-version 2026-08-01 \
  --dataset-revision DATASET_COMMIT
```

The builder writes the canonical, attributed index format. It only indexes rows where `type == "decision"`, extracts neutral citations from `citation`, deduplicates matching records and omits the full `text` field. If the dataset revision is unavailable, omit it and the builder records `unknown`.

Inspect an index or migrate a legacy flat-array index without changing the original file:

```bash
caselaw-guard au-index stats data/australia-index.json
caselaw-guard au-index migrate legacy-index.json --output canonical-index.json
```

Version 0.3.0 reads canonical and legacy indexes. New builds always use the canonical format; legacy support is transitional and has no scheduled removal version.

To update an installed index, fetch the new explicit version with `--force`
after reviewing its provenance. The command verifies everything before
replacement. To roll back, point `CASELAW_GUARD_AU_INDEX` at a previously
verified index file; indexes are not updated automatically.

## REST API

Run the API:

```bash
CASELAW_GUARD_AU_INDEX=/absolute/path/to/australia-index.json \
  uvicorn caselaw_guard.api:app --reload
```

Request:

```bash
curl -X POST http://127.0.0.1:8000/verify \
  -H 'content-type: application/json' \
  -d '{"text":"Obergefell v. Hodges, 576 U.S. 644"}'
```

Response shape:

```json
{
  "pass": false,
  "results": [
    {
      "citation": "576 U.S. 644",
      "start_index": 22,
      "end_index": 34,
      "jurisdiction_guess": "us",
      "provider": null,
      "normalized_citation": "576 U.S. 644",
      "authority": null,
      "source_url": null,
      "status": "unsupported_format",
      "confidence": 0.0,
      "error_message": "No configured adapter supports this citation format.",
      "candidates": [],
      "provider_metadata": {}
    }
  ]
}
```

The same application provides read-only Australian routes:

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness and Australian index status. |
| `GET /v1/au/citations/{citation}` | Normalize and look up one Australian neutral citation. |
| `GET /v1/au/index/metadata` | Index version, source, revision, licence and attribution. |
| `GET /v1/au/index/stats` | Counts by court and year, date range and ambiguities. |

See [the Australian API reference](docs/australian-api.md) and [self-hosting guide](docs/self-hosting.md).

## MCP Server

Run the local stdio MCP server directly to confirm it starts:

```bash
caselaw-guard-mcp
```

The server exposes one tool, `verify_case_law_text`, which accepts `text` and returns the same JSON report shape as the CLI and REST API.

The MCP extra uses Python SDK v2. It supports modern `2026-07-28` sessions and
earlier 2025-era protocol clients through the same stdio server and tool.

For agent configuration, prefer an absolute path to the installed script so the agent does not depend on shell startup files or `PATH` inheritance. In a local checkout, that path is typically:

```text
/path/to/caselaw-guard/.venv/bin/caselaw-guard-mcp
```

### Codex

Add the server to `~/.codex/config.toml`:

```toml
[mcp_servers.caselaw-guard]
command = "/path/to/caselaw-guard/.venv/bin/caselaw-guard-mcp"

[mcp_servers.caselaw-guard.env]
CASELAW_GUARD_COURTLISTENER_TOKEN = "your-courtlistener-token"
CASELAW_GUARD_AU_INDEX = "/absolute/path/to/australia-index.json"
CASELAW_GUARD_CACHE = "/absolute/path/to/courtlistener-cache.json"
CASELAW_GUARD_CACHE_TTL_DAYS = "30"
```

### Claude Code

Register the same stdio server with `claude mcp add-json`:

```json
{
  "type": "stdio",
  "command": "/path/to/caselaw-guard/.venv/bin/caselaw-guard-mcp",
  "env": {
    "CASELAW_GUARD_COURTLISTENER_TOKEN": "your-courtlistener-token",
    "CASELAW_GUARD_AU_INDEX": "/absolute/path/to/australia-index.json",
    "CASELAW_GUARD_CACHE": "/absolute/path/to/courtlistener-cache.json",
    "CASELAW_GUARD_CACHE_TTL_DAYS": "30"
  }
}
```

```bash
claude mcp add-json caselaw-guard '{"type":"stdio","command":"/path/to/caselaw-guard/.venv/bin/caselaw-guard-mcp","env":{"CASELAW_GUARD_COURTLISTENER_TOKEN":"your-courtlistener-token","CASELAW_GUARD_AU_INDEX":"/absolute/path/to/australia-index.json","CASELAW_GUARD_CACHE":"/absolute/path/to/courtlistener-cache.json","CASELAW_GUARD_CACHE_TTL_DAYS":"30"}}'
```

### MCP Environment

Set only the provider environment variables you need:

| Variable | Required | Purpose |
| --- | --- | --- |
| `CASELAW_GUARD_COURTLISTENER_TOKEN` | Required for U.S. citation lookup | Enables the CourtListener adapter. |
| `CASELAW_GUARD_AU_INDEX` | Required for Australian citation lookup | Points to a compact Australian citation index JSON file. |
| `CASELAW_GUARD_CACHE` | Optional | Enables the CourtListener lookup cache. |
| `CASELAW_GUARD_CACHE_TTL_DAYS` | Optional | Overrides the default CourtListener cache TTL of 30 days. |

Omit provider environment variables for adapters you do not want to enable.

### Troubleshooting

- Use an absolute `command` path if the agent cannot find `caselaw-guard-mcp`.
- Verify installation with `/path/to/caselaw-guard/.venv/bin/caselaw-guard-mcp`; stop it with `Ctrl+C` after it starts.
- Confirm provider environment variables are present in the agent MCP config, not only in your interactive shell.
- If the server exits with an MCP install hint, reinstall with `python3 -m pip install -e ".[mcp]"`.

## Adapters

### CourtListener

The CourtListener adapter verifies U.S. citations through the CourtListener citation lookup API. Configure it with `CASELAW_GUARD_COURTLISTENER_TOKEN` or `--courtlistener-token`.

The adapter sends citation components such as `volume=576`, `reporter=U.S.`, and `page=644`, not the full source document.

Set `CASELAW_GUARD_CACHE` to enable a persistent cache without passing `--cache`; set `CASELAW_GUARD_CACHE_TTL_DAYS` to change expiry.

### Australia

The Australian adapter verifies neutral citations against a local JSON metadata index derived from the Open Australian Legal Corpus. Australian support is part of the base package: there is no `[au]` extra and no `openbench` dependency.

The extractor and normalizer accept bracketed, parenthesised and bare years, case-insensitive court codes, extra whitespace and paragraph pinpoints. These inputs all look up `[1992] HCA 23`:

```text
[1992] HCA 23
(1992) HCA 23
1992 HCA 23
[1992] hca 23 at [10]
```

Court codes may contain letters and numbers, including `FedCFamC1A`. Reported citations such as `(1992) 175 CLR 1` remain outside this Australian neutral-citation parser.

The canonical index is a metadata object keyed by normalized citation:

```json
{
  "index_version": "2026-08-01",
  "dataset_revision": "DATASET_COMMIT",
  "license": "CC-BY-4.0",
  "record_count": 1,
  "entries": {
    "[1992] HCA 23": {
      "normalized_citation": "[1992] HCA 23",
      "case_name": "Mabo v Queensland (No 2)",
      "court_code": "HCA",
      "date": "1992-06-03",
      "source_urls": ["https://eresources.hcourt.gov.au/showCase/1992/HCA/23"]
    }
  }
}
```

If more than one index row has the same `normalized_citation`, the adapter returns `ambiguous` and exposes each match in `candidates`.

Every Australian result, including `not_found` and `unsupported_format`, carries the loaded index's provenance in `provider_metadata`. A legacy index reports `index_format: legacy` and marks unavailable provenance as `unknown`.

The fixture and published index artifacts are CC-BY-4.0 data derived from the Open Australian Legal Corpus by Isaacus. See [DATA_SOURCES.md](DATA_SOURCES.md), the [approved coverage report](benchmarks/reports/australian-index-2026-08-01.json) and [LICENSE-DATA](LICENSE-DATA). The Python source remains Apache-2.0.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ".[dev]"
.venv/bin/python -m pytest
```

Install MCP support from a local checkout:

```bash
.venv/bin/python -m pip install -e ".[mcp]"
```

## Benchmarks

Run the AusLaw Citation Benchmark extraction eval manually to measure Australian neutral citation coverage:

```bash
.venv/bin/python scripts/eval_auslaw_benchmark.py \
  --output .cache/caselaw-guard/auslaw-citation-benchmark/report.json
```

By default, the script downloads the benchmark test split from Hugging Face into `.cache/caselaw-guard/auslaw-citation-benchmark/roc_test.json` and reuses it on later runs. Pass `--refresh` to redownload it, or `--input /path/to/roc_test.json` to evaluate a local copy.

To measure end-to-end verification coverage against a compact Australian index, pass `--au-index`:

```bash
.venv/bin/python scripts/eval_auslaw_benchmark.py \
  --au-index /absolute/path/to/australia-index.json \
  --output .cache/caselaw-guard/auslaw-citation-benchmark/verification-report.json
```

Without `--au-index`, the eval measures extraction only. With `--au-index`, it also reports verification status counts and capped not-found or ambiguous examples.

## Release Readiness

The package build and manual PyPI publishing workflow are validated in CI. See `RELEASE.md` for the release checklist.

## Non-Goals For v0

- No proposition-support checking.
- No good-law or precedential-status analysis.
- No PDF or DOCX parsing.
- No legal advice.
