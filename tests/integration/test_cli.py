import json
from pathlib import Path

from typer.testing import CliRunner

from openbench.cli import app

CORPUS = Path(__file__).parent.parent.parent / "data" / "fixtures" / "corpus-fixture.jsonl"
FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"

runner = CliRunner()


def test_index_build_writes_valid_index(tmp_path: Path) -> None:
    out = tmp_path / "index.json"
    result = runner.invoke(app, ["index", "build", str(CORPUS), "--output", str(out)])
    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text())
    assert "[1992] HCA 23" in data["entries"]


def test_index_stats_prints_counts(tmp_path: Path) -> None:
    result = runner.invoke(app, ["index", "stats", str(FIXTURE)])
    assert result.exit_code == 0, result.stdout
    assert "record_count" in result.stdout
    assert "11" in result.stdout


def test_serve_help_lists_index_option() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--index" in result.stdout
