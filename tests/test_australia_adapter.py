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


def test_australian_adapter_reports_duplicate_neutral_citation_as_ambiguous(tmp_path):
    index = tmp_path / "index.json"
    index.write_text(
        """[
          {
            "citation": "First Case [2024] NSWSC 10",
            "normalized_citation": "[2024] NSWSC 10",
            "case_name": "First Case",
            "court": "Supreme Court of New South Wales",
            "date": "2024-01-01",
            "source_url": "https://example.test/first"
          },
          {
            "citation": "Second Case [2024] NSWSC 10",
            "normalized_citation": "[2024] NSWSC 10",
            "case_name": "Second Case",
            "court": "Supreme Court of New South Wales",
            "date": "2024-01-02",
            "source_url": "https://example.test/second"
          }
        ]""",
        encoding="utf-8",
    )

    report = verify_text("Ambiguous authority [2024] NSWSC 10.", adapters=[AustralianCorpusAdapter(index_path=index)])

    result = report.results[0]
    assert report.pass_ is False
    assert result.status == VerificationStatus.AMBIGUOUS
    assert result.authority is None
    assert [candidate.case_name for candidate in result.candidates] == ["First Case", "Second Case"]


def test_australian_adapter_rejects_invalid_index_schema(tmp_path):
    index = tmp_path / "index.json"
    index.write_text("""[{"citation": "Mabo v Queensland (No 2) [1992] HCA 23"}]""", encoding="utf-8")

    try:
        AustralianCorpusAdapter(index_path=index)
    except ValueError as error:
        assert "normalized_citation" in str(error)
    else:
        raise AssertionError("Expected invalid Australian index schema to fail.")


def test_australian_adapter_normalizes_whitespace(tmp_path):
    index = tmp_path / "index.json"
    index.write_text(
        """[
          {
            "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
            "normalized_citation": "[1992]   HCA   23",
            "case_name": "Mabo v Queensland (No 2)",
            "court": "High Court of Australia",
            "date": "1992-06-03",
            "source_url": "https://eresources.hcourt.gov.au/showCase/1992/HCA/23"
          }
        ]""",
        encoding="utf-8",
    )

    report = verify_text("Mabo v Queensland (No 2) [1992] HCA 23.", adapters=[AustralianCorpusAdapter(index_path=index)])

    assert report.pass_ is True
    assert report.results[0].normalized_citation == "[1992] HCA 23"
