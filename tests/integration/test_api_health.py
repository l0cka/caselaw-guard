from pathlib import Path

from fastapi.testclient import TestClient

from openbench.api import create_app

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_health_with_index_loaded() -> None:
    app = create_app(index_path=FIXTURE)
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "index_loaded": True}


def test_health_with_no_index() -> None:
    app = create_app(index_path=None)
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "index_loaded": False}
