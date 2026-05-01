from __future__ import annotations

from dataclasses import dataclass

from caselaw_guard.models import Authority, CitationMatch, VerificationStatus


@dataclass(slots=True)
class LookupResult:
    status: VerificationStatus
    normalized_citation: str | None = None
    authority: Authority | None = None
    source_url: str | None = None
    confidence: float = 0.0
    error_message: str | None = None


class CitationAdapter:
    name = "base"
    jurisdictions: frozenset[str] = frozenset()

    def supports(self, citation: CitationMatch) -> bool:
        return citation.jurisdiction_guess in self.jurisdictions

    def lookup(self, citation: CitationMatch) -> LookupResult:
        raise NotImplementedError
