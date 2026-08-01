"""Read-only, typed Australian citation index storage."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any, Self

from pydantic import ValidationError

from caselaw_guard.australia.courts import canonical_court_code, resolve_court
from caselaw_guard.australia.models import (
    UNKNOWN,
    IndexEntry,
    IndexFile,
    IndexMetadata,
    IndexProvenance,
    IndexStats,
)
from caselaw_guard.australia.normalization import normalize_citation


class IndexLoadError(RuntimeError):
    """The configured Australian index is missing, malformed, or invalid."""


class IndexStore:
    """An in-memory index keyed by normalized Australian neutral citation."""

    def __init__(
        self,
        entries_by_citation: Mapping[str, list[IndexEntry]],
        *,
        provenance: IndexProvenance,
        builder_version: str,
    ) -> None:
        self._entries = {citation: list(entries) for citation, entries in entries_by_citation.items()}
        self._provenance = provenance
        self._builder_version = builder_version
        self._stats = self._compute_stats()

    @classmethod
    def load(cls, path: str | Path) -> Self:
        index_path = Path(path)
        if not index_path.is_file():
            raise IndexLoadError(f"index file not found: {index_path}")
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise IndexLoadError(f"could not read index file {index_path}: {error}") from error
        except json.JSONDecodeError as error:
            raise IndexLoadError(f"index file is not valid JSON: {error}") from error
        try:
            if isinstance(raw, list):
                return cls._from_legacy(raw)
            return cls._from_canonical(raw)
        except (TypeError, ValueError, ValidationError) as error:
            raise IndexLoadError(f"index file failed validation: {error}") from error

    @classmethod
    def _from_canonical(cls, raw: object) -> Self:
        parsed = IndexFile.model_validate(raw)
        entries = {
            citation: value if isinstance(value, list) else [value] for citation, value in parsed.entries.items()
        }
        return cls(
            entries,
            provenance=IndexProvenance(
                index_version=parsed.index_version,
                generated_at=parsed.generated_at,
                source=parsed.source,
                dataset_revision=parsed.dataset_revision,
                license=parsed.license,
                attribution=parsed.attribution,
                index_format="canonical",
            ),
            builder_version=parsed.builder_version,
        )

    @classmethod
    def _from_legacy(cls, raw: list[object]) -> Self:
        entries: dict[str, list[IndexEntry]] = {}
        for row_number, row in enumerate(raw):
            if not isinstance(row, dict):
                raise ValueError(f"legacy row {row_number} must be an object")
            entry = _legacy_entry(row, row_number)
            entries.setdefault(entry.normalized_citation, []).append(entry)
        return cls(
            entries,
            provenance=IndexProvenance(
                index_version=UNKNOWN,
                generated_at=UNKNOWN,
                source=UNKNOWN,
                dataset_revision=UNKNOWN,
                license=UNKNOWN,
                attribution=UNKNOWN,
                index_format="legacy",
            ),
            builder_version=UNKNOWN,
        )

    def lookup(self, normalized_citation: str) -> list[IndexEntry]:
        return list(self._entries.get(normalized_citation, ()))

    def provenance(self) -> IndexProvenance:
        return self._provenance

    def metadata(self) -> IndexMetadata:
        return IndexMetadata(
            **self._provenance.model_dump(),
            record_count=self._stats.record_count,
            builder_version=self._builder_version,
        )

    def stats(self) -> IndexStats:
        return self._stats

    def to_index_file(
        self,
        *,
        index_version: str = "legacy-migrated",
        generated_at: str,
        builder_version: str,
    ) -> IndexFile:
        """Return this store in canonical format without altering its source file."""
        entries: dict[str, IndexEntry | list[IndexEntry]] = {
            citation: values[0] if len(values) == 1 else values for citation, values in self._entries.items()
        }
        provenance = self._provenance
        return IndexFile(
            index_version=index_version if provenance.index_format == "legacy" else provenance.index_version,
            generated_at=generated_at if provenance.index_format == "legacy" else provenance.generated_at,
            builder_version=builder_version if provenance.index_format == "legacy" else self._builder_version,
            source=UNKNOWN if provenance.index_format == "legacy" else provenance.source,
            dataset_revision=UNKNOWN if provenance.index_format == "legacy" else provenance.dataset_revision,
            license=UNKNOWN if provenance.index_format == "legacy" else provenance.license,
            attribution=UNKNOWN if provenance.index_format == "legacy" else provenance.attribution,
            record_count=len(entries),
            entries=entries,
        )

    def _compute_stats(self) -> IndexStats:
        by_court: Counter[str] = Counter()
        by_year: Counter[str] = Counter()
        dates: list[date] = []
        for values in self._entries.values():
            for entry in values:
                by_court[entry.court_code] += 1
                by_year[str(entry.date.year)] += 1
                dates.append(entry.date)
        return IndexStats(
            record_count=len(self._entries),
            ambiguous_count=sum(len(values) > 1 for values in self._entries.values()),
            by_court=dict(by_court),
            by_year=dict(by_year),
            earliest_date=min(dates, default=None),
            latest_date=max(dates, default=None),
        )


def _legacy_entry(row: dict[str, Any], row_number: int) -> IndexEntry:
    normalized_input = row.get("normalized_citation") or row.get("citation")
    if not isinstance(normalized_input, str):
        raise ValueError(f"legacy row {row_number} is missing normalized_citation")
    normalized = normalize_citation(normalized_input)
    if not normalized.ok or normalized.normalized is None or normalized.court_code is None:
        raise ValueError(f"legacy row {row_number} has an invalid normalized_citation")
    case_name = row.get("case_name") or row.get("citation")
    source_url = row.get("source_url") or row.get("url")
    raw_date = row.get("date")
    if not isinstance(case_name, str) or not case_name.strip():
        raise ValueError(f"legacy row {row_number} is missing case_name")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError(f"legacy row {row_number} is missing source_url")
    try:
        entry_date = date.fromisoformat(str(raw_date)[:10])
    except (TypeError, ValueError) as error:
        raise ValueError(f"legacy row {row_number} has an invalid date") from error
    court_code = canonical_court_code(str(row.get("court_code") or normalized.court_code))
    court, jurisdiction = resolve_court(court_code)
    return IndexEntry(
        normalized_citation=normalized.normalized,
        citation=str(row.get("citation") or normalized_input),
        case_name=case_name,
        court=str(row["court"]) if row.get("court") else court,
        court_code=court_code,
        jurisdiction=str(row["jurisdiction"]) if row.get("jurisdiction") else jurisdiction,
        date=entry_date,
        source_urls=[source_url],
        source=str(row.get("source") or UNKNOWN),
        source_record_ids=[str(row.get("id") or source_url)],
        indexed_at=entry_date,
        license=str(row.get("license") or UNKNOWN),
    )
