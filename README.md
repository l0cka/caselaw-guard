# CaseLaw Guard

CaseLaw Guard is an Apache-2.0 verifier for agents and drafting workflows that need to fail closed on fabricated case-law citations.

The v0 guarantee is deliberately narrow: **citation existence only**. It does not decide whether a case supports a legal proposition, whether a case remains good law, or whether any output is legal advice.

## What It Does

- Extracts case-law citations locally from plain text or Markdown.
- Verifies citations through configured legal-source adapters.
- Sends only citation strings or citation components to external providers by default.
- Returns stable JSON that agents can use to block, retry, or show unresolved citations.
- Exits non-zero from the CLI when any extracted citation is not verified.

## Install

After the first PyPI release, install the base package from PyPI:

```bash
python3 -m pip install caselaw-guard
```

From a local checkout for development:

```bash
python3 -m pip install -e ".[dev]"
```

After the first PyPI release, install with local MCP server support:

```bash
python3 -m pip install "caselaw-guard[mcp]"
```

## CLI

Verify a Markdown or text draft:

```bash
caselaw-guard verify draft.md \
  --courtlistener-token "$CASELAW_GUARD_COURTLISTENER_TOKEN" \
  --au-index examples/australia_index.sample.json
```

Read from stdin:

```bash
printf 'Mabo v Queensland (No 2) [1992] HCA 23\n' \
  | caselaw-guard verify - --no-courtlistener --au-index examples/australia_index.sample.json
```

The CLI exits `0` only when every extracted citation is `verified`; otherwise it exits `1`.

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
  --output data/australia-index.json
```

The builder only indexes rows where `type == "decision"`, extracts neutral citations from `citation`, and omits the full `text` field.

## REST API

Run the API:

```bash
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

## MCP Server

Install the optional MCP extra when using CaseLaw Guard from local agents. From a local checkout:

```bash
python3 -m pip install -e ".[mcp]"
```

Run the local stdio MCP server directly to confirm it starts:

```bash
caselaw-guard-mcp
```

The server exposes one tool, `verify_case_law_text`, which accepts `text` and returns the same JSON report shape as the CLI and REST API.

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

The Australian adapter verifies neutral citations against a local JSON metadata index derived from sources such as the Open Australian Legal Corpus. A record should include a neutral citation and whatever authority metadata is available:

```json
[
  {
    "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
    "normalized_citation": "[1992] HCA 23",
    "case_name": "Mabo v Queensland (No 2)",
    "court": "High Court of Australia",
    "date": "1992-06-03",
    "source_url": "https://eresources.hcourt.gov.au/showCase/1992/HCA/23"
  }
]
```

If more than one index row has the same `normalized_citation`, the adapter returns `ambiguous` and exposes each match in `candidates`.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ".[dev]"
.venv/bin/python -m pytest
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

The package build is validated in CI, but publishing is not enabled yet. See `RELEASE.md` for the manual v0.1 release checklist.

## Non-Goals For v0

- No proposition-support checking.
- No good-law or precedential-status analysis.
- No PDF or DOCX parsing.
- No legal advice.
