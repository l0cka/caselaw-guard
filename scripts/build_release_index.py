"""Build and validate a release-grade Australian citation index."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema

from caselaw_guard.australia.index_builder import write_index

DATASET = "isaacus/open-australian-legal-corpus"
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "australia-index.schema.json"


def _dataset_revision() -> str:
    """Resolve the source revision, returning unknown rather than guessing."""
    from huggingface_hub import HfApi

    revision = HfApi().dataset_info(DATASET).sha
    return revision or "unknown"


def _stream_decisions_to_jsonl(output_path: Path, *, revision: str | None) -> int:
    from datasets import load_dataset

    kwargs: dict[str, object] = {"split": "train", "streaming": True}
    if revision is not None:
        kwargs["revision"] = revision
    dataset = load_dataset(DATASET, **kwargs)
    count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for row in dataset:
            if row.get("type") != "decision":
                continue
            projection: dict[str, Any] = {
                "type": "decision",
                "citation": row.get("citation") or "",
                "url": row.get("url") or "",
                "date": str(row.get("date") or "")[:10],
                "jurisdiction": row.get("jurisdiction") or "",
                "id": row.get("id") or row.get("url") or "",
            }
            output.write(json.dumps(projection, ensure_ascii=False) + "\n")
            count += 1
    return count


def _validate(index_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    validator.validate(index)


def _write_checksums(paths: list[Path], output_path: Path) -> None:
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in paths]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compress(index_path: Path, compressed_path: Path) -> None:
    import zstandard as zstd

    compressed_path.write_bytes(zstd.ZstdCompressor(level=19).compress(index_path.read_bytes()))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index-version", required=True)
    parser.add_argument(
        "--dataset-revision",
        help="Exact upstream revision to record; defaults to the resolved revision or unknown for --corpus.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        help="Local Open Australian Legal Corpus JSONL. Enables an offline release build.",
    )
    args = parser.parse_args(argv)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.corpus is not None:
        corpus_path = args.corpus
        revision = args.dataset_revision or "unknown"
        if not corpus_path.is_file():
            parser.error(f"corpus file not found: {corpus_path}")
        print(f"building from local corpus {corpus_path} with dataset revision {revision}")
        write_index(
            corpus_path,
            args.output,
            index_version=args.index_version,
            dataset_revision=revision,
        )
    else:
        revision = args.dataset_revision or _dataset_revision()
        with tempfile.TemporaryDirectory(prefix="caselaw-guard-index-") as directory:
            corpus_path = Path(directory) / "decisions.jsonl"
            count = _stream_decisions_to_jsonl(
                corpus_path,
                revision=None if revision == "unknown" else revision,
            )
            print(f"projected {count} decision records from {DATASET}@{revision}")
            write_index(
                corpus_path,
                args.output,
                index_version=args.index_version,
                dataset_revision=revision,
            )

    _validate(args.output)
    compressed_path = args.output.with_suffix(args.output.suffix + ".zst")
    _compress(args.output, compressed_path)
    checksum_path = args.output.with_suffix(args.output.suffix + ".sha256")
    _write_checksums([args.output, compressed_path], checksum_path)
    print(f"wrote {args.output}, {compressed_path} and {checksum_path}")


if __name__ == "__main__":
    main()
