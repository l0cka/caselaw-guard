import pytest

from caselaw_guard.extractors import extract_citations


@pytest.mark.parametrize(
    "court_code",
    [
        "NSWCATAP",
        "NSWLEC",
        "NSWADT",
        "NSWCATAD",
        "NSWADTAP",
        "NSWIRComm",
        "NSWCATOD",
        "NSWMT",
        "NSWCATEN",
    ],
)
def test_extract_citations_recognizes_benchmark_missed_au_court_codes(court_code):
    citation = f"[2014] {court_code} 17"

    matches = extract_citations(f"See Collins v Urban {citation}.")

    assert [(match.text, match.jurisdiction_guess, match.groups["court"]) for match in matches] == [
        (citation, "au", court_code)
    ]
