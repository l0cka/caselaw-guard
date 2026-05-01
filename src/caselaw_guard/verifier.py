from __future__ import annotations

from pathlib import Path
from typing import Sequence

from caselaw_guard.adapters import build_adapters
from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.extractors import extract_citations
from caselaw_guard.models import CitationMatch, VerificationReport, VerificationResult, VerificationStatus


def verify_text(text: str, *, adapters: Sequence[CitationAdapter] | None = None) -> VerificationReport:
    active_adapters = list(adapters) if adapters is not None else build_adapters()
    results = [_verify_citation(citation, active_adapters) for citation in extract_citations(text)]
    return VerificationReport(pass_=all(result.status == VerificationStatus.VERIFIED for result in results), results=results)


def verify_file(path: str | Path, *, adapters: Sequence[CitationAdapter] | None = None) -> VerificationReport:
    text = Path(path).read_text(encoding="utf-8")
    return verify_text(text, adapters=adapters)


def _verify_citation(citation: CitationMatch, adapters: Sequence[CitationAdapter]) -> VerificationResult:
    adapter = next((candidate for candidate in adapters if candidate.supports(citation)), None)
    if adapter is None:
        return _result_from_lookup(
            citation,
            provider=None,
            lookup=LookupResult(
                status=VerificationStatus.UNSUPPORTED_FORMAT,
                normalized_citation=citation.text,
                error_message="No configured adapter supports this citation format.",
            ),
        )

    try:
        lookup = adapter.lookup(citation)
    except Exception as error:  # defensive boundary: provider bugs must fail closed
        lookup = LookupResult(
            status=VerificationStatus.PROVIDER_ERROR,
            normalized_citation=citation.text,
            error_message=str(error),
        )

    return _result_from_lookup(citation, provider=adapter.name, lookup=lookup)


def _result_from_lookup(citation: CitationMatch, *, provider: str | None, lookup: LookupResult) -> VerificationResult:
    return VerificationResult(
        citation=citation.text,
        start_index=citation.start_index,
        end_index=citation.end_index,
        jurisdiction_guess=citation.jurisdiction_guess,
        provider=provider,
        normalized_citation=lookup.normalized_citation,
        authority=lookup.authority,
        source_url=lookup.source_url,
        status=lookup.status,
        confidence=lookup.confidence,
        error_message=lookup.error_message,
        candidates=lookup.candidates,
        provider_metadata=lookup.provider_metadata,
    )
