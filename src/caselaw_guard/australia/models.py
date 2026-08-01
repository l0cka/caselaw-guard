"""Typed Australian index and lookup contracts."""

from __future__ import annotations

from datetime import date as Date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from caselaw_guard.australia.courts import canonical_court_code
from caselaw_guard.australia.normalization import normalize_citation

ATTRIBUTION = (
    "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw "
    "Guard (metadata extraction, normalisation and deduplication)."
)
UNKNOWN = "unknown"


class AustralianLookupStatus(StrEnum):
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED_FORMAT = "unsupported_format"


class IndexEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized_citation: str
    citation: str
    case_name: str
    court: str | None = None
    court_code: str
    jurisdiction: str | None = None
    date: Date
    source_urls: Annotated[list[str], Field(min_length=1)]
    source: str
    source_record_ids: Annotated[list[str], Field(min_length=1)]
    indexed_at: Date
    license: str

    @model_validator(mode="after")
    def validate_citation_key(self) -> IndexEntry:
        result = normalize_citation(self.normalized_citation)
        if not result.ok or result.normalized != self.normalized_citation:
            raise ValueError("normalized_citation must be a canonical neutral citation")
        if self.court_code != canonical_court_code(self.court_code):
            raise ValueError("court_code must use canonical spelling")
        return self


class IndexFile(BaseModel):
    """Canonical on-disk Australian citation index."""

    model_config = ConfigDict(extra="forbid")

    index_version: str
    generated_at: str
    builder_version: str
    source: str
    dataset_revision: str = UNKNOWN
    license: str
    attribution: str = ATTRIBUTION
    record_count: int = Field(ge=0)
    entries: dict[str, IndexEntry | Annotated[list[IndexEntry], Field(min_length=2)]]

    @model_validator(mode="after")
    def validate_entry_keys(self) -> IndexFile:
        if self.record_count != len(self.entries):
            raise ValueError("record_count must equal the number of normalized citation keys")
        for citation, value in self.entries.items():
            entries = value if isinstance(value, list) else [value]
            if not entries:
                raise ValueError(f"entries[{citation!r}] cannot be empty")
            if any(entry.normalized_citation != citation for entry in entries):
                raise ValueError(f"entries[{citation!r}] must use its normalized citation key")
        return self


class IndexProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index_version: str
    generated_at: str
    source: str
    dataset_revision: str
    license: str
    attribution: str
    index_format: str


class IndexMetadata(IndexProvenance):
    record_count: int
    builder_version: str


class IndexStats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_count: int
    ambiguous_count: int
    by_court: dict[str, int]
    by_year: dict[str, int]
    earliest_date: Date | None
    latest_date: Date | None


class AustralianLookupResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_citation: str
    normalized_citation: str | None
    status: AustralianLookupStatus
    entries: tuple[IndexEntry, ...]
    provenance: IndexProvenance
    rejection_reason: str | None
    confidence: float
