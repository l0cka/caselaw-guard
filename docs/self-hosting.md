# Self-hosting Australian citation lookup

CaseLaw Guard is read-only and stateless apart from its configured Australian
index and optional CourtListener cache.

## 1. Get an index

Fetch an explicit version with the package command. It verifies the compressed
asset and JSON digest, canonical schema and Isaacus attribution before the
output is replaced:

```bash
caselaw-guard au-index fetch 2026-08-01 --output australian-index.json
```

The command refuses an existing output unless `--force` is supplied, refuses
symbolic links, keeps temporary files beside the output, and leaves an
existing valid index untouched if any check fails. It uses only the fixed
GitHub release URLs derived from the requested `YYYY-MM-DD` version. Checksums
protect release-asset integrity, not a compromised repository or release
account.

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

Monitor `GET /health` and alert when `index_loaded` is `false`. Fetch a new
explicit version with `--force`, validate the installed file with
`caselaw-guard au-index stats`, and restart the process. Version 0.3.0 does
not hot-reload indexes.

To roll back, point `CASELAW_GUARD_AU_INDEX` at a previously verified index
file and restart the process. Do not mutate a historical index in place.

## 4. Preserve attribution

The fixture and full Australian index artifacts are CC-BY-4.0 data derived from
the Open Australian Legal Corpus by Isaacus. Keep `LICENSE-DATA` and the
canonical attribution with every redistribution. The API includes it in every
Australian lookup response and the metadata route. The approved
[2026-08-01 coverage report](../benchmarks/reports/australian-index-2026-08-01.json)
documents the benchmark's snapshot limits; a `not_found` result does not prove
that a case does not exist.

This service is not an official court or government source and does not provide
legal advice.
