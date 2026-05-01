from caselaw_guard import verify_text
from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.models import Authority, CitationMatch, VerificationStatus


class RecordingAdapter(CitationAdapter):
    name = "recording"
    jurisdictions = frozenset({"us"})

    def __init__(self):
        self.queries = []

    def supports(self, citation: CitationMatch) -> bool:
        return citation.jurisdiction_guess == "us"

    def lookup(self, citation: CitationMatch) -> LookupResult:
        self.queries.append(citation.text)
        if citation.text == "576 U.S. 644":
            return LookupResult(
                status=VerificationStatus.VERIFIED,
                normalized_citation="576 U.S. 644",
                authority=Authority(
                    case_name="Obergefell v. Hodges",
                    court="Supreme Court of the United States",
                    date="2015-06-26",
                    source_url="https://www.courtlistener.com/opinion/2812209/obergefell-v-hodges/",
                ),
                source_url="https://www.courtlistener.com/opinion/2812209/obergefell-v-hodges/",
                confidence=1.0,
                provider_metadata={"source": "fixture"},
            )
        return LookupResult(status=VerificationStatus.NOT_FOUND, normalized_citation=citation.text)


def test_verify_text_returns_stable_contract_and_fails_closed_for_unresolved_citations():
    adapter = RecordingAdapter()
    document = (
        "Obergefell v. Hodges, 576 U.S. 644, is real. "
        "Imaginary v. Fictional, 999 U.S. 999, is not."
    )

    report = verify_text(document, adapters=[adapter])

    assert report.pass_ is False
    assert [result.status for result in report.results] == [
        VerificationStatus.VERIFIED,
        VerificationStatus.NOT_FOUND,
    ]
    assert adapter.queries == ["576 U.S. 644", "999 U.S. 999"]
    assert all(document not in query for query in adapter.queries)

    payload = report.model_dump(by_alias=True)
    assert payload["pass"] is False
    assert set(payload["results"][0]) == {
        "citation",
        "start_index",
        "end_index",
        "jurisdiction_guess",
        "provider",
        "normalized_citation",
        "authority",
        "source_url",
        "status",
        "confidence",
        "error_message",
        "candidates",
        "provider_metadata",
    }


def test_verify_text_passes_when_document_has_no_citations():
    report = verify_text("This paragraph has no case-law citation.", adapters=[RecordingAdapter()])

    assert report.pass_ is True
    assert report.results == []
