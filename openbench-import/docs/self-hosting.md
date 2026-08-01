# Self-hosting openbench

openbench is read-only and stateless apart from the index file. Self-hosting boils down to: get an `index.json`, point `--index` at it, run `uvicorn`.

## 1. Get an index file

You have two options.

### Option A: download a release artifact

Once openbench publishes tagged releases, each one will include `index-<version>.json.zst`. Decompress and use:

```bash
zstd -d index-2026-05-01.json.zst -o index.json
```

### Option B: build from the upstream corpus

Download the Open Australian Legal Corpus from HuggingFace and convert it to a JSONL with the fields openbench expects:

- `type` — must be `"decision"` for inclusion
- `citation` — full citation string, e.g. `Mabo v Queensland (No 2) [1992] HCA 23`
- `url` — source URL
- `date` — ISO date `YYYY-MM-DD`
- `jurisdiction` — string (any value; openbench rederives jurisdiction from the court code)
- `id` — stable record id

Then:

```bash
uv run openbench index build /path/to/corpus.jsonl --output index.json
```

## 2. Run the server

```bash
uv run openbench serve --index $(pwd)/index.json --host 0.0.0.0 --port 8000
```

Or via the env var:

```bash
export AUS_CASE_INDEX=$(pwd)/index.json
uv run uvicorn 'openbench.api:create_app' --factory --host 0.0.0.0 --port 8000
```

## 3. Health checks

`GET /health` always returns 200 with `{"status":"ok","index_loaded":true|false}`. Use the body to alert on `false`.

## 4. Updating the index

Stop the server, replace `index.json`, restart. There is no hot reload in v1.

## 5. Disclaimers

You are responsible for displaying the CC-BY-4.0 attribution wherever you expose openbench results. The attribution is included in every API response's `provenance.attribution` and in `/v1/au/index/metadata.attribution`.
