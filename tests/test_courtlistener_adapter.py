import httpx

from caselaw_guard.adapters.courtlistener import CourtListenerAdapter
from caselaw_guard.models import CitationMatch, VerificationStatus


def test_courtlistener_adapter_sends_citation_components_not_document_text():
    seen_body = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_body
        seen_body = request.content.decode()
        return httpx.Response(
            200,
            json=[
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "status": 200,
                    "error_message": "",
                    "clusters": [
                        {
                            "case_name": "Obergefell v. Hodges",
                            "date_filed": "2015-06-26",
                            "court": "scotus",
                            "absolute_url": "/opinion/2812209/obergefell-v-hodges/",
                        }
                    ],
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(
        CitationMatch(
            text="576 U.S. 644",
            start_index=23,
            end_index=35,
            jurisdiction_guess="us",
        )
    )

    assert result.status == VerificationStatus.VERIFIED
    assert seen_body == "volume=576&reporter=U.S.&page=644"
    assert "Obergefell v. Hodges, 576 U.S. 644, appears in the draft" not in seen_body
