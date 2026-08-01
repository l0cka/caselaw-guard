# Self-hosting Australian citation lookup

CaseLaw Guard is read-only and stateless apart from its configured Australian
index and optional CourtListener cache.

## 1. Get an index

Download a versioned `australian-index-<version>.json.zst` release asset and
verify it against the published SHA-256 file before decompressing it:

```bash
zstd -d australian-index-2026-08-01.json.zst \
  -o australian-index-2026-08-01.json
```

Alternatively, build a canonical index from a local Open Australian Legal
Corpus JSONL export:

```bash
caselaw-guard au-index build corpus.jsonl \
  --output australian-index.json \
  --index-version 2026-08-01 \
  --dataset-revision DATASET_COMMIT
```

The builder needs `type`, `citation`, `url`, `date`, `jurisdiction` and a stable
`id`. It keeps decisions and does not copy judgment text into the index.

## 2. Run the server

```bash
export CASELAW_GUARD_AU_INDEX=/absolute/path/to/australian-index.json
uvicorn caselaw_guard.api:app --host 0.0.0.0 --port 8000
```

Set `CASELAW_GUARD_COURTLISTENER_TOKEN` only if this deployment also needs US
citation verification.

## 3. Monitor and update

Monitor `GET /health` and alert when `index_loaded` is `false`. Validate a new
file with `caselaw-guard au-index stats`, replace the configured file and
restart the process. Version 0.2.0 does not hot-reload indexes.

## 4. Preserve attribution

The fixture and full Australian index artifacts are CC-BY-4.0 data derived from
the Open Australian Legal Corpus by Isaacus. Keep `LICENSE-DATA` and the
canonical attribution with every redistribution. The API includes it in every
Australian lookup response and the metadata route.

This service is not an official court or government source and does not provide
legal advice. A `not_found` result is not proof that a case does not exist.
