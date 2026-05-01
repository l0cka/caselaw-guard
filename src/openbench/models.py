"""Pydantic models for the openbench API and index file."""

from datetime import date as _Date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ATTRIBUTION = (
    "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, "
    "modified by openbench (metadata extraction)."
)


class Status(StrEnum):
    verified = "verified"
    not_found = "not_found"
    ambiguous = "ambiguous"
    unsupported_format = "unsupported_format"
    index_unavailable = "index_unavailable"
    provider_error = "provider_error"


class IndexEntry(BaseModel):
    """A single deduplicated case entry in the index."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized_citation: str
    citation: str
    case_name: str
    court: str | None = None
    court_code: str
    jurisdiction: str | None = None
    date: _Date
    source_urls: Annotated[list[str], Field(min_length=1)]
    source: str
    source_record_ids: Annotated[list[str], Field(min_length=1)]
    indexed_at: _Date
    license: str


class Candidate(BaseModel):
    """A candidate entry returned for ambiguous lookups."""

    model_config = ConfigDict(extra="forbid")

    case_name: str
    court: str | None = None
    court_code: str
    jurisdiction: str | None = None
    date: _Date
    source_urls: list[str]


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_version: str | None = None
    source: str | None = None
    license: str | None = None
    dataset: str | None = None
    attribution: str | None = None


class LookupResponse(BaseModel):
    """Response from /v1/au/citations/{citation}."""

    model_config = ConfigDict(extra="forbid")

    citation: str
    normalized_citation: str | None = None
    status: Status
    case_name: str | None = None
    court: str | None = None
    court_code: str | None = None
    jurisdiction: str | None = None
    date: _Date | None = None
    source_urls: list[str] | None = None
    sources: list[str] | None = None
    confidence: float
    candidates: list[Candidate]
    provenance: Provenance | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    index_loaded: bool


class IndexMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_version: str
    generated_at: str
    record_count: int
    sources: list[str]
    license: str
    builder_version: str
    attribution: str
    dataset: str
    dataset_version: str


class IndexStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_count: int
    ambiguous_count: int
    by_court: dict[str, int]
    by_year: dict[str, int]
    earliest_date: _Date | None
    latest_date: _Date | None


class IndexFile(BaseModel):
    """Top-level structure of a serialised index file on disk."""

    model_config = ConfigDict(extra="forbid")

    index_version: str
    generated_at: str
    builder_version: str
    source: str
    license: str
    record_count: int
    entries: dict[str, IndexEntry | list[IndexEntry]]
