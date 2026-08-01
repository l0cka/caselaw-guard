"""The single application-level Australian citation lookup service."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from caselaw_guard.australia.index_store import IndexStore
from caselaw_guard.australia.models import AustralianLookupResult, AustralianLookupStatus
from caselaw_guard.australia.normalization import is_neutral_citation_shape, normalize_citation


class AustralianCitationService:
    """Normalize, query, and classify Australian neutral-citation lookups."""

    def __init__(self, store: IndexStore) -> None:
        self._store = store

    @classmethod
    def load(cls, index_path: str | Path) -> Self:
        return cls(IndexStore.load(index_path))

    @property
    def store(self) -> IndexStore:
        return self._store

    def lookup(self, raw_citation: str) -> AustralianLookupResult:
        normalized = normalize_citation(raw_citation)
        provenance = self._store.provenance()
        if not normalized.ok or normalized.normalized is None:
            status = (
                AustralianLookupStatus.NOT_FOUND
                if is_neutral_citation_shape(raw_citation)
                else AustralianLookupStatus.UNSUPPORTED_FORMAT
            )
            reason = "year_out_of_range" if status is AustralianLookupStatus.NOT_FOUND else "malformed_neutral_citation"
            return AustralianLookupResult(
                raw_citation=raw_citation,
                normalized_citation=None,
                status=status,
                entries=(),
                provenance=provenance,
                rejection_reason=reason,
                confidence=0.0,
            )
        entries = tuple(self._store.lookup(normalized.normalized))
        if not entries:
            status, confidence = AustralianLookupStatus.NOT_FOUND, 0.0
        elif len(entries) == 1:
            status, confidence = AustralianLookupStatus.VERIFIED, 1.0
        else:
            status, confidence = AustralianLookupStatus.AMBIGUOUS, 0.5
        return AustralianLookupResult(
            raw_citation=raw_citation,
            normalized_citation=normalized.normalized,
            status=status,
            entries=entries,
            provenance=provenance,
            rejection_reason=None,
            confidence=confidence,
        )
