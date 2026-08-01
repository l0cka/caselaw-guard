"""In-memory JSON-backed index store with O(1) citation lookup."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from pydantic import ValidationError

from openbench.models import (
    ATTRIBUTION,
    IndexEntry,
    IndexFile,
    IndexMetadata,
    IndexStats,
)


class IndexLoadError(RuntimeError):
    """Raised when an index file is missing, malformed, or fails validation."""


class IndexStore:
    """Read-only in-memory store of `IndexEntry` objects keyed by `normalized_citation`."""

    def __init__(
        self,
        entries_by_citation: Mapping[str, list[IndexEntry]],
        index_version: str,
        generated_at: str,
        builder_version: str,
        source: str,
        license: str,  # matches schema field name
        dataset: str = "isaacus/open-australian-legal-corpus",
        dataset_version: str = "unknown",
    ) -> None:
        self._entries: dict[str, list[IndexEntry]] = {
            k: list(v) for k, v in entries_by_citation.items()
        }
        self._index_version = index_version
        self._generated_at = generated_at
        self._builder_version = builder_version
        self._source = source
        self._license = license
        self._dataset = dataset
        self._dataset_version = dataset_version
        self._stats = self._compute_stats()

    @classmethod
    def load(cls, path: Path | str) -> Self:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise IndexLoadError(f"index file not found: {p}")
        try:
            raw = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise IndexLoadError(f"index file is not valid JSON: {e}") from e
        try:
            parsed = IndexFile.model_validate(raw)
        except ValidationError as e:
            raise IndexLoadError(f"index file failed schema validation: {e}") from e

        normalised: dict[str, list[IndexEntry]] = {}
        for citation, value in parsed.entries.items():
            normalised[citation] = value if isinstance(value, list) else [value]

        return cls(
            entries_by_citation=normalised,
            index_version=parsed.index_version,
            generated_at=parsed.generated_at,
            builder_version=parsed.builder_version,
            source=parsed.source,
            license=parsed.license,
        )

    def lookup(self, normalized_citation: str) -> list[IndexEntry]:
        return list(self._entries.get(normalized_citation, ()))

    def metadata(self) -> IndexMetadata:
        return IndexMetadata(
            index_version=self._index_version,
            generated_at=self._generated_at,
            record_count=self._stats.record_count,
            sources=[self._source],
            license=self._license,
            builder_version=self._builder_version,
            attribution=ATTRIBUTION,
            dataset=self._dataset,
            dataset_version=self._dataset_version,
        )

    def stats(self) -> IndexStats:
        return self._stats

    @property
    def index_version(self) -> str:
        return self._index_version

    @property
    def source(self) -> str:
        return self._source

    @property
    def license(self) -> str:
        return self._license

    def _compute_stats(self) -> IndexStats:
        record_count = len(self._entries)
        ambiguous_count = 0
        by_court: Counter[str] = Counter()
        by_year: Counter[str] = Counter()
        earliest = None
        latest = None
        for entries in self._entries.values():
            if len(entries) > 1:
                ambiguous_count += 1
            for e in entries:
                by_court[e.court_code] += 1
                by_year[str(e.date.year)] += 1
                earliest = e.date if earliest is None or e.date < earliest else earliest
                latest = e.date if latest is None or e.date > latest else latest
        return IndexStats(
            record_count=record_count,
            ambiguous_count=ambiguous_count,
            by_court=dict(by_court),
            by_year=dict(by_year),
            earliest_date=earliest,
            latest_date=latest,
        )


__all__ = ["IndexLoadError", "IndexStore"]
