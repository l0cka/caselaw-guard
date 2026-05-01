import os
import subprocess
import sys
from pathlib import Path

import pytest

import caselaw_guard.mcp_server as mcp_server
from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.mcp_server import verify_case_law_text


FIXTURE_INDEX = Path(__file__).parent / "fixtures" / "australia_index.json"


def test_mcp_tool_handler_returns_existing_verification_report_shape():
    payload = verify_case_law_text(
        text="Known: Mabo v Queensland (No 2) [1992] HCA 23.",
        adapters=[AustralianCorpusAdapter(index_path=FIXTURE_INDEX)],
    )

    assert payload["pass"] is True
    assert payload["results"][0]["citation"] == "[1992] HCA 23"
    assert payload["results"][0]["status"] == "verified"
    assert "provider_metadata" in payload["results"][0]


def test_mcp_module_imports_without_starting_server():
    completed = subprocess.run(
        [sys.executable, "-c", "import caselaw_guard.mcp_server"],
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0


def test_mcp_entrypoint_explains_missing_extra(monkeypatch, capsys):
    def raise_missing_extra():
        raise RuntimeError("MCP support is not installed. Install it with: python3 -m pip install 'caselaw-guard[mcp]'")

    monkeypatch.setattr(mcp_server, "create_mcp_server", raise_missing_extra)

    with pytest.raises(SystemExit) as exit_info:
        mcp_server.main()

    assert exit_info.value.code == 1
    assert "caselaw-guard[mcp]" in capsys.readouterr().err
