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

```bash
python3 -m pip install -e ".[dev]"
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

## Non-Goals For v0

- No proposition-support checking.
- No good-law or precedential-status analysis.
- No PDF or DOCX parsing.
- No MCP server.
- No legal advice.
