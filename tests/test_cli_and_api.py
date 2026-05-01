import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.api import create_app


FIXTURE_INDEX = Path(__file__).parent / "fixtures" / "australia_index.json"


def test_cli_exits_nonzero_when_any_citation_is_unverified(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("Known: [1992] HCA 23. Fake: [2099] HCA 999.", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "caselaw_guard.cli",
            "verify",
            str(draft),
            "--no-courtlistener",
            "--au-index",
            str(FIXTURE_INDEX),
        ],
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["pass"] is False
    assert [result["status"] for result in payload["results"]] == ["verified", "not_found"]


def test_api_returns_pass_flag_and_results_with_injected_adapters():
    app = create_app(adapters=[AustralianCorpusAdapter(index_path=FIXTURE_INDEX)])
    client = TestClient(app)

    response = client.post("/verify", json={"text": "Known: [1992] HCA 23."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pass"] is True
    assert payload["results"][0]["citation"] == "[1992] HCA 23"
