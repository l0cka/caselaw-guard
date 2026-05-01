import os

import pytest

from caselaw_guard.adapters.courtlistener import CourtListenerAdapter
from caselaw_guard.models import CitationMatch, VerificationStatus


@pytest.mark.integration
def test_courtlistener_live_lookup_verifies_known_us_citation():
    token = os.getenv("CASELAW_GUARD_COURTLISTENER_TOKEN")
    if not token:
        pytest.skip("CASELAW_GUARD_COURTLISTENER_TOKEN is not set.")

    adapter = CourtListenerAdapter(api_token=token)

    result = adapter.lookup(
        CitationMatch(
            text="576 U.S. 644",
            start_index=0,
            end_index=12,
            jurisdiction_guess="us",
            groups={"volume": "576", "reporter": "U.S.", "page": "644"},
        )
    )

    assert result.status == VerificationStatus.VERIFIED
    assert result.normalized_citation == "576 U.S. 644"
