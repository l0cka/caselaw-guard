# Australian API reference

CaseLaw Guard exposes Australian citation lookup from the same FastAPI
application as `POST /verify`. The service is read-only and uses the local file
configured by `CASELAW_GUARD_AU_INDEX`.

## Health

`GET /health` always returns `200`:

```json
{"status": "ok", "index_loaded": true}
```

If `index_loaded` is `false`, the Australian lookup, metadata and stats routes
return `503` with `{"status":"index_unavailable"}`. `POST /verify` remains
available for any other configured adapters.

## Citation lookup

URL-encode the citation and call `GET /v1/au/citations/{citation}`:

```bash
curl "http://127.0.0.1:8000/v1/au/citations/%5B1992%5D%20HCA%2023"
```

A verified response contains the normalized citation, authority metadata and
the provenance of the loaded index:

```json
{
  "citation": "[1992] HCA 23",
  "normalized_citation": "[1992] HCA 23",
  "status": "verified",
  "confidence": 1.0,
  "candidates": [],
  "provenance": {
    "index_version": "fixture-2026-08-01",
    "generated_at": "2026-08-01T00:00:00Z",
    "source": "open-australian-legal-corpus",
    "dataset_revision": "fixture",
    "license": "CC-BY-4.0",
    "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw Guard (metadata extraction, normalisation and deduplication).",
    "index_format": "canonical"
  },
  "case_name": "Mabo v Queensland (No 2)",
  "court": "High Court of Australia",
  "court_code": "HCA",
  "jurisdiction": "cth",
  "date": "1992-06-03",
  "source_urls": ["https://eresources.hcourt.gov.au/showCase/1992/HCA/23"],
  "sources": ["open-australian-legal-corpus"]
}
```

The status is `verified`, `not_found`, `ambiguous` or `unsupported_format`.
Ambiguous responses put every matching authority in `candidates` and do not
select one. Every status includes `provenance`.

Accepted neutral-citation forms include `[1992] HCA 23`, `(1992) HCA 23`,
`1992 HCA 23` and `[1992] hca 23 at [10]`. They all normalize to
`[1992] HCA 23`. Reported citations such as `(1992) 175 CLR 1` are outside this
parser.

## Index metadata and statistics

`GET /v1/au/index/metadata` returns the index version, generation time, source,
dataset revision, licence, attribution, format, record count and builder
version.

`GET /v1/au/index/stats` returns normalized citation-key count, ambiguity count,
counts by court and year, and the earliest and latest decision dates.

An absent citation only means that it is absent from the configured index
snapshot. Verify important matters against an authorised source.
