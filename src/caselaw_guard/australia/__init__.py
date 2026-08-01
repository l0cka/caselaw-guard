"""Australian neutral-citation indexing and lookup."""

from caselaw_guard.australia.index_builder import build_index, migrate_index, write_index
from caselaw_guard.australia.index_store import IndexLoadError, IndexStore
from caselaw_guard.australia.models import (
    ATTRIBUTION,
    AustralianLookupResult,
    AustralianLookupStatus,
    IndexEntry,
    IndexFile,
    IndexProvenance,
)
from caselaw_guard.australia.service import AustralianCitationService

__all__ = [
    "ATTRIBUTION",
    "AustralianCitationService",
    "AustralianLookupResult",
    "AustralianLookupStatus",
    "IndexEntry",
    "IndexFile",
    "IndexLoadError",
    "IndexProvenance",
    "IndexStore",
    "build_index",
    "migrate_index",
    "write_index",
]
