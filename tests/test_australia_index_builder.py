import json
import os
import subprocess
import sys

from caselaw_guard.australia import build_index, write_index


def test_build_australian_index_filters_non_decisions_and_missing_citations(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "index.json"
    corpus.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "decision",
                        "jurisdiction": "cth",
                        "source": "High Court of Australia",
                        "date": "1992-06-03",
                        "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                        "url": "https://eresources.hcourt.gov.au/showCase/1992/HCA/23",
                        "text": "Large body text should not be copied into the compact index.",
                    }
                ),
                json.dumps(
                    {
                        "type": "legislation",
                        "citation": "Privacy Act 1988 (Cth)",
                        "url": "https://example.test/legislation",
                    }
                ),
                json.dumps({"type": "decision", "citation": "", "url": "https://example.test/missing"}),
            ]
        ),
        encoding="utf-8",
    )

    index = write_index(corpus, output, index_version="test-index")

    assert index.record_count == 1
    assert index.index_version == "test-index"
    assert "[1992] HCA 23" in index.entries
    serialized = json.loads(output.read_text(encoding="utf-8"))
    assert serialized["record_count"] == 1
    assert "text" not in serialized["entries"]["[1992] HCA 23"]


def test_au_index_cli_builds_index(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "index.json"
    corpus.write_text(
        json.dumps(
            {
                "type": "decision",
                "source": "High Court of Australia",
                "date": "1983-07-01",
                "citation": "Commonwealth v Tasmania [1983] HCA 21",
                "url": "https://eresources.hcourt.gov.au/showCase/1983/HCA/21",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "caselaw_guard.cli", "au-index", "build", str(corpus), "--output", str(output)],
        env={**os.environ, "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    index = json.loads(output.read_text(encoding="utf-8"))
    assert index["record_count"] == 1
    assert index["entries"]["[1983] HCA 21"]["normalized_citation"] == "[1983] HCA 21"
    assert '"record_count": 1' in completed.stdout


def test_build_australian_index_accepts_mixed_case_neutral_court_code(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "type": "decision",
                "source": "Industrial Relations Commission of New South Wales",
                "date": "2012-05-01",
                "citation": "Example v Respondent [2012] NSWIRComm 42",
                "url": "https://example.test/nswircomm/42",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    index = build_index(corpus)

    assert index.record_count == 1
    entry = index.entries["[2012] NSWIRComm 42"]
    assert not isinstance(entry, list)
    assert entry.normalized_citation == "[2012] NSWIRComm 42"
