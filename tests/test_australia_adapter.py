from pathlib import Path

from caselaw_guard import verify_text
from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.models import VerificationStatus


FIXTURE_INDEX = Path(__file__).parent / "fixtures" / "australia_index.json"


def test_australian_adapter_verifies_known_neutral_citation_from_fixture():
    adapter = AustralianCorpusAdapter(index_path=FIXTURE_INDEX)

    report = verify_text("Mabo v Queensland (No 2) [1992] HCA 23 remains a landmark case.", adapters=[adapter])

    assert report.pass_ is True
    result = report.results[0]
    assert result.status == VerificationStatus.VERIFIED
    assert result.citation == "[1992] HCA 23"
    assert result.provider == "open-australian-legal-corpus"
    assert result.authority.case_name == "Mabo v Queensland (No 2)"
    assert result.source_url == "https://eresources.hcourt.gov.au/showCase/1992/HCA/23"


def test_australian_adapter_reports_unknown_neutral_citation_as_not_found():
    adapter = AustralianCorpusAdapter(index_path=FIXTURE_INDEX)

    report = verify_text("The agent invented Applicant v Minister [2099] HCA 999.", adapters=[adapter])

    assert report.pass_ is False
    assert report.results[0].status == VerificationStatus.NOT_FOUND
    assert report.results[0].normalized_citation == "[2099] HCA 999"
