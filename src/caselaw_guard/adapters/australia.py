from __future__ import annotations

from pathlib import Path

from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.australia import (
    AustralianCitationService,
    AustralianLookupResult,
    AustralianLookupStatus,
    IndexEntry,
    IndexLoadError,
)
from caselaw_guard.models import Authority, CitationMatch, VerificationStatus

_STATUS_MAP = {
    AustralianLookupStatus.VERIFIED: VerificationStatus.VERIFIED,
    AustralianLookupStatus.NOT_FOUND: VerificationStatus.NOT_FOUND,
    AustralianLookupStatus.AMBIGUOUS: VerificationStatus.AMBIGUOUS,
    AustralianLookupStatus.UNSUPPORTED_FORMAT: VerificationStatus.UNSUPPORTED_FORMAT,
}


class AustralianCorpusAdapter(CitationAdapter):
    name = "open-australian-legal-corpus"
    jurisdictions = frozenset({"au"})

    def __init__(self, index_path: str | Path):
        self.index_path = Path(index_path)
        try:
            self.service = AustralianCitationService.load(self.index_path)
        except IndexLoadError as error:
            raise ValueError(
                f"Could not load Australian index at {self.index_path}: {error}. "
                "Build a valid index with: caselaw-guard au-index build CORPUS --output INDEX"
            ) from error

    def lookup(self, citation: CitationMatch) -> LookupResult:
        return map_australian_lookup(self.service.lookup(citation.text))


def map_australian_lookup(result: AustralianLookupResult) -> LookupResult:
    authority = _authority_from_entry(result.entries[0]) if result.status is AustralianLookupStatus.VERIFIED else None
    candidates = (
        [_authority_from_entry(entry) for entry in result.entries]
        if result.status is AustralianLookupStatus.AMBIGUOUS
        else []
    )
    normalized = result.normalized_citation
    if normalized is None and result.rejection_reason == "year_out_of_range":
        normalized = result.raw_citation

    return LookupResult(
        status=_STATUS_MAP[result.status],
        normalized_citation=normalized,
        authority=authority,
        source_url=authority.source_url if authority else None,
        confidence=result.confidence,
        error_message=result.rejection_reason,
        candidates=candidates,
        provider_metadata=result.provenance.model_dump(mode="json"),
    )


def _authority_from_entry(entry: IndexEntry) -> Authority:
    source_url = entry.source_urls[0]
    return Authority(
        case_name=entry.case_name,
        court=entry.court,
        date=entry.date.isoformat(),
        source_url=source_url,
        metadata={
            "court_code": entry.court_code,
            "jurisdiction": entry.jurisdiction,
            "source_urls": list(entry.source_urls),
            "source": entry.source,
            "license": entry.license,
        },
    )
