from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def _client() -> TestClient:
    app = create_app(index_path=FIXTURE)
    return TestClient(app)


def _get(citation: str) -> dict:
    with _client() as client:
        r = client.get(f"/v1/au/citations/{quote(citation, safe='')}")
    assert r.status_code == 200, r.text
    return r.json()


def test_lookup_verified_mabo() -> None:
    body = _get("[1992] HCA 23")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"
    assert body["case_name"] == "Mabo v Queensland (No 2)"
    assert body["court"] == "High Court of Australia"
    assert body["jurisdiction"] == "cth"
    assert body["confidence"] == 1.0
    assert body["candidates"] == []
    assert body["sources"] == ["open-australian-legal-corpus"]
    assert body["provenance"]["license"] == "CC-BY-4.0"


def test_lookup_pinpoint_stripped() -> None:
    body = _get("[1992] HCA 23 [10]")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"


def test_lookup_paren_year_form() -> None:
    body = _get("(1992) HCA 23")
    assert body["status"] == "verified"
    assert body["normalized_citation"] == "[1992] HCA 23"


def test_lookup_not_found() -> None:
    body = _get("[2099] HCA 999")
    assert body["status"] == "not_found"
    assert body["confidence"] == 0.0
    assert body["candidates"] == []


def test_lookup_unsupported_format_plain_text() -> None:
    body = _get("Mabo")
    assert body["status"] == "unsupported_format"
    assert body["confidence"] == 0.0


def test_lookup_unsupported_reported_citation() -> None:
    body = _get("(1992) 175 CLR 1")
    assert body["status"] == "unsupported_format"


def test_lookup_ambiguous() -> None:
    body = _get("[2024] NSWSC 9999")
    assert body["status"] == "ambiguous"
    assert body["confidence"] == 0.5
    assert "case_name" not in body or body["case_name"] is None
    assert len(body["candidates"]) == 2
    names = {c["case_name"] for c in body["candidates"]}
    assert names == {"First Synthetic Case", "Second Synthetic Case"}


def test_response_includes_provenance_attribution_for_verified() -> None:
    body = _get("[1992] HCA 23")
    assert "Isaacus" in body["provenance"]["attribution"]
