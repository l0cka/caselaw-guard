# openbench API reference

Base URL when self-hosted: `http://127.0.0.1:8000`.

All responses are JSON. Encode the citation in the path with standard URL encoding.

## `GET /health`

```json
{"status": "ok", "index_loaded": true}
```

`200` always. `index_loaded: false` means lookup/metadata/stats will return `503`.

## `GET /v1/au/citations/{citation}`

### Verified

```json
{
  "citation": "[1992] HCA 23",
  "normalized_citation": "[1992] HCA 23",
  "status": "verified",
  "case_name": "Mabo v Queensland (No 2)",
  "court": "High Court of Australia",
  "court_code": "HCA",
  "jurisdiction": "cth",
  "date": "1992-06-03",
  "source_urls": ["https://example.org/mabo"],
  "sources": ["open-australian-legal-corpus"],
  "confidence": 1.0,
  "candidates": [],
  "provenance": {
    "index_version": "2026-05-01",
    "source": "open-australian-legal-corpus",
    "license": "CC-BY-4.0",
    "dataset": "isaacus/open-australian-legal-corpus",
    "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction)."
  }
}
```

### Not found

```json
{
  "citation": "[2099] HCA 999",
  "normalized_citation": "[2099] HCA 999",
  "status": "not_found",
  "confidence": 0.0,
  "candidates": []
}
```

### Ambiguous

```json
{
  "citation": "[2024] NSWSC 9999",
  "normalized_citation": "[2024] NSWSC 9999",
  "status": "ambiguous",
  "confidence": 0.5,
  "candidates": [
    {"case_name": "First Synthetic Case", "court_code": "NSWSC", "court": "Supreme Court of New South Wales", "jurisdiction": "nsw", "date": "2024-01-01", "source_urls": ["https://example.org/first"]},
    {"case_name": "Second Synthetic Case", "court_code": "NSWSC", "court": "Supreme Court of New South Wales", "jurisdiction": "nsw", "date": "2024-01-15", "source_urls": ["https://example.org/second"]}
  ]
}
```

### Unsupported format

```json
{
  "citation": "Mabo",
  "status": "unsupported_format",
  "confidence": 0.0,
  "candidates": []
}
```

### Index unavailable (503)

```json
{"status": "index_unavailable"}
```

## Accepted citation forms

| Input | Normalised |
|---|---|
| `[1992] HCA 23` | `[1992] HCA 23` |
| `(1992) HCA 23` | `[1992] HCA 23` |
| `1992 HCA 23` | `[1992] HCA 23` |
| `[1992] HCA 23 [10]` (pinpoint) | `[1992] HCA 23` |
| `[1992] HCA 23 at [10]` | `[1992] HCA 23` |
| `(1992) 175 CLR 1` (reported) | rejected as `unsupported_format` in v1 |

## `GET /v1/au/index/metadata`

```json
{
  "index_version": "fixture-2026-05-01",
  "generated_at": "2026-05-01T00:00:00Z",
  "record_count": 11,
  "sources": ["open-australian-legal-corpus"],
  "license": "CC-BY-4.0",
  "builder_version": "0.1.0",
  "attribution": "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by openbench (metadata extraction).",
  "dataset": "isaacus/open-australian-legal-corpus",
  "dataset_version": "unknown"
}
```

## `GET /v1/au/index/stats`

```json
{
  "record_count": 11,
  "ambiguous_count": 1,
  "by_court": {"HCA": 5, "FCAFC": 1, "FCA": 1, "NSWCA": 1, "NSWSC": 2, "VSCA": 1, "QCA": 1},
  "by_year": {"1951": 1, "1983": 1, "1992": 1, "1996": 1, "2002": 1, "2013": 1, "2017": 1, "2018": 1, "2019": 1, "2020": 1, "2024": 2},
  "earliest_date": "1951-03-09",
  "latest_date": "2024-01-15"
}
```
