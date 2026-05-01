import httpx
import pytest

from caselaw_guard.adapters import build_adapters
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


@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [
        (404, VerificationStatus.NOT_FOUND),
        (400, VerificationStatus.UNSUPPORTED_FORMAT),
        (429, VerificationStatus.RATE_LIMITED),
    ],
)
def test_courtlistener_adapter_maps_per_citation_status_codes(status_code, expected_status):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=[
                    {
                        "citation": "1 U.S. 200",
                        "normalized_citations": ["1 U.S. 200"],
                        "status": status_code,
                        "error_message": "lookup detail",
                        "clusters": [],
                    }
                ],
            )
        )
    )
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(
        CitationMatch(
            text="1 U.S. 200",
            start_index=0,
            end_index=10,
            jurisdiction_guess="us",
            groups={"volume": "1", "reporter": "U.S.", "page": "200"},
        )
    )

    assert result.status == expected_status
    assert result.error_message == "lookup detail"


def test_courtlistener_adapter_exposes_ambiguous_candidates():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=[
                    {
                        "citation": "1 H. 150",
                        "normalized_citations": ["1 Handy 150", "1 Haw. 150", "1 Hill 150"],
                        "status": 300,
                        "error_message": "",
                        "clusters": [
                            {
                                "case_name": "Louis v. Steamboat Buckeye",
                                "court": "Ohio Reports",
                                "date_filed": "1854-01-01",
                                "absolute_url": "/opinion/1/louis/",
                            },
                            {
                                "case_name": "Fell v. Parke",
                                "court": "Hawaii Reports",
                                "date_filed": "1856-01-01",
                                "absolute_url": "/opinion/2/fell/",
                            },
                        ],
                    }
                ],
            )
        )
    )
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(CitationMatch(text="1 H. 150", start_index=0, end_index=8, jurisdiction_guess="us"))

    assert result.status == VerificationStatus.AMBIGUOUS
    assert result.authority is None
    assert result.normalized_citation == "1 Handy 150"
    assert [candidate.case_name for candidate in result.candidates] == [
        "Louis v. Steamboat Buckeye",
        "Fell v. Parke",
    ]


def test_courtlistener_adapter_maps_http_429_with_provider_metadata():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, json={"wait_until": "2026-05-01T00:01:00Z"})
        )
    )
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(CitationMatch(text="576 U.S. 644", start_index=0, end_index=12, jurisdiction_guess="us"))

    assert result.status == VerificationStatus.RATE_LIMITED
    assert result.provider_metadata == {"wait_until": "2026-05-01T00:01:00Z"}


def test_courtlistener_adapter_maps_non_json_response_to_provider_error():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text="not json")))
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(CitationMatch(text="576 U.S. 644", start_index=0, end_index=12, jurisdiction_guess="us"))

    assert result.status == VerificationStatus.PROVIDER_ERROR
    assert "non-JSON" in result.error_message


def test_courtlistener_adapter_maps_network_errors_to_provider_error():
    def handler(request):
        raise httpx.ConnectError("network down", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(api_token="test-token", client=client)

    result = adapter.lookup(CitationMatch(text="576 U.S. 644", start_index=0, end_index=12, jurisdiction_guess="us"))

    assert result.status == VerificationStatus.PROVIDER_ERROR
    assert "network down" in result.error_message


def test_courtlistener_cache_is_opt_in_and_stores_successful_results_only(tmp_path):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json=[
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "status": 200,
                    "error_message": "",
                    "clusters": [{"case_name": "Obergefell v. Hodges"}],
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(api_token="test-token", client=client, cache_path=tmp_path / "cl-cache.json")
    citation = CitationMatch(text="576 U.S. 644", start_index=0, end_index=12, jurisdiction_guess="us")

    assert adapter.lookup(citation).status == VerificationStatus.VERIFIED
    assert adapter.lookup(citation).status == VerificationStatus.VERIFIED

    assert calls == 1


def test_courtlistener_without_cache_calls_provider_each_time():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(api_token="test-token", client=client)
    citation = CitationMatch(text="1 U.S. 200", start_index=0, end_index=10, jurisdiction_guess="us")

    adapter.lookup(citation)
    adapter.lookup(citation)

    assert calls == 2


def test_courtlistener_cache_respects_ttl(tmp_path):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(
        api_token="test-token",
        client=client,
        cache_path=tmp_path / "cl-cache.json",
        cache_ttl_days=0,
    )
    citation = CitationMatch(text="1 U.S. 200", start_index=0, end_index=10, jurisdiction_guess="us")

    adapter.lookup(citation)
    adapter.lookup(citation)

    assert calls == 2


def test_courtlistener_cache_does_not_store_provider_error_or_rate_limit(tmp_path):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"wait_until": "2026-05-01T00:01:00Z"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = CourtListenerAdapter(api_token="test-token", client=client, cache_path=tmp_path / "cl-cache.json")
    citation = CitationMatch(text="576 U.S. 644", start_index=0, end_index=12, jurisdiction_guess="us")

    adapter.lookup(citation)
    adapter.lookup(citation)

    assert calls == 2


def test_build_adapters_reads_opt_in_cache_environment(monkeypatch, tmp_path):
    cache_path = tmp_path / "cl-cache.json"
    monkeypatch.setenv("CASELAW_GUARD_COURTLISTENER_TOKEN", "test-token")
    monkeypatch.setenv("CASELAW_GUARD_CACHE", str(cache_path))
    monkeypatch.setenv("CASELAW_GUARD_CACHE_TTL_DAYS", "7")

    adapters = build_adapters()

    assert len(adapters) == 1
    assert isinstance(adapters[0], CourtListenerAdapter)
    assert adapters[0].cache_path == cache_path
    assert adapters[0].cache_ttl.days == 7
