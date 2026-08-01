from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_metadata() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["index_version"] == "fixture-2026-05-01"
    assert body["sources"] == ["open-australian-legal-corpus"]
    assert body["license"] == "CC-BY-4.0"
    assert "Isaacus" in body["attribution"]


def test_stats() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["record_count"] == 11
    assert body["ambiguous_count"] == 1
    assert body["by_court"]["HCA"] >= 1


def test_lookup_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get(f"/v1/au/citations/{quote('[1992] HCA 23')}")
    assert r.status_code == 503
    assert r.json()["status"] == "index_unavailable"


def test_metadata_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/metadata")
    assert r.status_code == 503


def test_stats_returns_503_when_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/v1/au/index/stats")
    assert r.status_code == 503
