"""Build a release-grade openbench index from the Isaacus HF corpus.

Usage:
    uv run --extra release python scripts/build_release_index.py \
        --output index.json --index-version 2026-05-01

Steps:
  1. Stream the Isaacus dataset, keeping only `decision` records.
  2. Project to the JSONL fields openbench expects.
  3. Pipe to `openbench.index_builder.build_index`.
  4. Validate against `schemas/index.schema.json`.
  5. Write `index.json` and `index.json.zst`.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import jsonschema
import zstandard as zstd
from datasets import load_dataset

from openbench.index_builder import build_index

DATASET = "isaacus/open-australian-legal-corpus"
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "index.schema.json"


def _stream_decisions_to_jsonl(out_path: Path) -> int:
    ds = load_dataset(DATASET, split="train", streaming=True)
    n = 0
    with out_path.open("w") as f:
        for row in ds:
            if row.get("type") != "decision":
                continue
            projection = {
                "type": "decision",
                "citation": row.get("citation") or "",
                "url": row.get("url") or "",
                "date": (row.get("date") or "")[:10],
                "jurisdiction": row.get("jurisdiction") or "",
                "id": row.get("id") or row.get("url") or "",
            }
            f.write(json.dumps(projection, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--index-version", required=True)
    args = ap.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        jsonl_path = Path(tmp.name)
    print(f"streaming {DATASET} -> {jsonl_path}")
    n = _stream_decisions_to_jsonl(jsonl_path)
    print(f"wrote {n} decision records")

    print("building index")
    data = build_index(jsonl_path, index_version=args.index_version)

    print("validating against schema")
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(data, schema)

    print(f"writing {args.output}")
    args.output.write_text(json.dumps(data, ensure_ascii=False))

    zst_path = args.output.with_suffix(args.output.suffix + ".zst")
    print(f"compressing {zst_path}")
    cctx = zstd.ZstdCompressor(level=19)
    zst_path.write_bytes(cctx.compress(args.output.read_bytes()))
    print(f"done: {args.output.stat().st_size} bytes raw, {zst_path.stat().st_size} bytes zst")


if __name__ == "__main__":
    main()
