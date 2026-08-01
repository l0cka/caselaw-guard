"""Build and migrate canonical Australian citation indexes."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterator
from datetime import UTC, date, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from caselaw_guard.australia.courts import resolve_court
from caselaw_guard.australia.index_store import IndexStore
from caselaw_guard.australia.models import ATTRIBUTION, UNKNOWN, IndexEntry, IndexFile
from caselaw_guard.australia.normalization import extract_case_name_and_citation, normalize_citation

SOURCE_NAME = "open-australian-legal-corpus"
LICENSE = "CC-BY-4.0"


def build_index(
    corpus_path: str | Path,
    *,
    index_version: str | None = None,
    indexed_at: date | None = None,
    dataset_revision: str | None = None,
) -> IndexFile:
    """Build a canonical index from Open Australian Legal Corpus JSONL."""
    today = indexed_at or date.today()
    grouped: dict[str, dict[tuple[str, date], dict[str, Any]]] = defaultdict(dict)
    for row in _read_jsonl(Path(corpus_path)):
        if row.get("type") != "decision":
            continue
        raw_citation = row.get("citation")
        if not isinstance(raw_citation, str):
            continue
        case_name, normalized_citation = extract_case_name_and_citation(raw_citation)
        entry_date = _parse_date(row.get("date"))
        source_url = row.get("url")
        if case_name is None or normalized_citation is None or entry_date is None or not source_url:
            continue
        result = normalize_citation(normalized_citation)
        assert result.court_code is not None  # normalized_citation came from the normalizer
        court, jurisdiction = resolve_court(result.court_code)
        bucket = grouped[normalized_citation]
        key = (case_name, entry_date)
        record_id = str(row.get("id") or source_url)
        if key not in bucket:
            bucket[key] = {
                "normalized_citation": normalized_citation,
                "citation": raw_citation,
                "case_name": case_name,
                "court": court,
                "court_code": result.court_code,
                "jurisdiction": jurisdiction,
                "date": entry_date,
                "source_urls": [],
                "source": SOURCE_NAME,
                "source_record_ids": [],
                "indexed_at": today,
                "license": LICENSE,
            }
        entry = bucket[key]
        if source_url not in entry["source_urls"]:
            entry["source_urls"].append(source_url)
        if record_id not in entry["source_record_ids"]:
            entry["source_record_ids"].append(record_id)
    entries = {citation: _entry_or_entries(bucket.values()) for citation, bucket in grouped.items()}
    return IndexFile(
        index_version=index_version or today.isoformat(),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        builder_version=_builder_version(),
        source=SOURCE_NAME,
        dataset_revision=dataset_revision or UNKNOWN,
        license=LICENSE,
        attribution=ATTRIBUTION,
        record_count=len(entries),
        entries=entries,
    )


def write_index(corpus_path: str | Path, output_path: str | Path, **kwargs: Any) -> IndexFile:
    index = build_index(corpus_path, **kwargs)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return index


def migrate_index(input_path: str | Path, output_path: str | Path) -> IndexFile:
    """Write a canonical copy of a canonical or legacy index without touching input."""
    store = IndexStore.load(input_path)
    migrated = store.to_index_file(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        builder_version=_builder_version(),
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(migrated.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return migrated


def _entry_or_entries(values: Any) -> IndexEntry | list[IndexEntry]:
    entries = [IndexEntry.model_validate(value) for value in values]
    return entries[0] if len(entries) == 1 else entries


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as corpus:
        for line in corpus:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _builder_version() -> str:
    try:
        return version("caselaw-guard")
    except PackageNotFoundError:
        return "0.2.0"
