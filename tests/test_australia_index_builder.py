import json
import os
import subprocess
import sys

from caselaw_guard.australia_index import build_australian_index


def test_build_australian_index_filters_decisions_and_counts_skipped_rows(tmp_path):
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
                "{not valid json",
            ]
        ),
        encoding="utf-8",
    )

    stats = build_australian_index(corpus, output)

    assert stats.records_written == 1
    assert stats.skipped_non_decision == 1
    assert stats.skipped_missing_citation == 1
    assert stats.skipped_malformed == 1
    index = json.loads(output.read_text(encoding="utf-8"))
    assert index == [
        {
            "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
            "normalized_citation": "[1992] HCA 23",
            "case_name": "Mabo v Queensland (No 2)",
            "court": "High Court of Australia",
            "jurisdiction": "cth",
            "date": "1992-06-03",
            "source_url": "https://eresources.hcourt.gov.au/showCase/1992/HCA/23",
        }
    ]


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
    assert json.loads(output.read_text(encoding="utf-8"))[0]["normalized_citation"] == "[1983] HCA 21"
    assert '"records_written": 1' in completed.stdout


def test_build_australian_index_accepts_mixed_case_neutral_court_code(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "index.json"
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

    stats = build_australian_index(corpus, output)

    assert stats.records_written == 1
    assert json.loads(output.read_text(encoding="utf-8"))[0]["normalized_citation"] == "[2012] NSWIRComm 42"
