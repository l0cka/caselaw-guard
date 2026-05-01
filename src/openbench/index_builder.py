"""Build an openbench index dict from a corpus JSONL file.

Input format: one JSON object per line, with at least the fields
  type (str), citation (str), url (str), date (str ISO),
  jurisdiction (str), id (str)

Behaviour:
  - filters records where type != "decision"
  - extracts neutral citation + case name via openbench.normalization
  - groups records by normalized_citation
  - merges records sharing (normalized_citation, case_name, date) into one entry
    (with a deduplicated list of source_urls and source_record_ids)
  - emits a top-level dict matching schemas/index.schema.json
  - record_count is the number of distinct citation keys (not the sum of entries)
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from openbench import __version__ as openbench_version
from openbench.courts import resolve_court
from openbench.normalization import extract_case_name_and_citation

SOURCE_NAME = "open-australian-legal-corpus"
LICENSE = "CC-BY-4.0"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def build_index(
    corpus_path: Path | str,
    *,
    index_version: str | None = None,
    indexed_at: date | None = None,
) -> dict[str, Any]:
    rows = _read_jsonl(Path(corpus_path))
    today = indexed_at or date.today()
    version = index_version or today.isoformat()

    # group: normalized_citation -> dedup_key -> merged entry (mutable dict)
    grouped: dict[str, dict[tuple[str, str], dict[str, Any]]] = defaultdict(dict)

    for row in rows:
        if row.get("type") != "decision":
            continue
        case_name, normalized = extract_case_name_and_citation(row.get("citation") or "")
        if normalized is None or case_name is None:
            continue
        d = _parse_date(row.get("date") or "")
        if d is None:
            continue

        court_code = normalized.split()[1]
        court_name, jurisdiction = resolve_court(court_code)
        url = row.get("url") or ""
        record_id = row.get("id") or url

        dedup_key = (case_name, d.isoformat())
        bucket = grouped[normalized]
        if dedup_key in bucket:
            entry = bucket[dedup_key]
            if url and url not in entry["source_urls"]:
                entry["source_urls"].append(url)
            if record_id and record_id not in entry["source_record_ids"]:
                entry["source_record_ids"].append(record_id)
        else:
            bucket[dedup_key] = {
                "normalized_citation": normalized,
                "citation": row.get("citation") or "",
                "case_name": case_name,
                "court": court_name,
                "court_code": court_code,
                "jurisdiction": jurisdiction,
                "date": d.isoformat(),
                "source_urls": [url] if url else [],
                "source": SOURCE_NAME,
                "source_record_ids": [record_id] if record_id else [],
                "indexed_at": today.isoformat(),
                "license": LICENSE,
            }

    entries: dict[str, Any] = {}
    for citation, bucket in grouped.items():
        merged = list(bucket.values())
        entries[citation] = merged[0] if len(merged) == 1 else merged

    generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    return {
        "index_version": version,
        "generated_at": generated_at,
        "builder_version": openbench_version,
        "source": SOURCE_NAME,
        "license": LICENSE,
        "record_count": len(entries),  # distinct citation keys
        "entries": entries,
    }
