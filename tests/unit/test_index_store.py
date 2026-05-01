import json
from pathlib import Path

import pytest

from openbench.index_store import IndexLoadError, IndexStore

FIXTURE = Path(__file__).parent.parent.parent / "data" / "fixtures" / "index.json"


def test_load_fixture_index() -> None:
    store = IndexStore.load(FIXTURE)
    assert store.metadata().record_count == 11


def test_lookup_verified_case() -> None:
    store = IndexStore.load(FIXTURE)
    entries = store.lookup("[1992] HCA 23")
    assert len(entries) == 1
    assert entries[0].case_name == "Mabo v Queensland (No 2)"
    assert entries[0].source_urls == [
        "https://example.org/mabo",
        "https://example.org/mabo-mirror",
    ]


def test_lookup_ambiguous_case_returns_multiple() -> None:
    store = IndexStore.load(FIXTURE)
    entries = store.lookup("[2024] NSWSC 9999")
    assert len(entries) == 2
    assert {e.case_name for e in entries} == {"First Synthetic Case", "Second Synthetic Case"}


def test_lookup_unknown_returns_empty() -> None:
    store = IndexStore.load(FIXTURE)
    assert store.lookup("[2099] HCA 999") == []


def test_stats_aggregates_by_court_and_year() -> None:
    store = IndexStore.load(FIXTURE)
    stats = store.stats()
    assert stats.record_count == 11
    assert stats.ambiguous_count == 1
    assert stats.by_court["HCA"] >= 1
    assert "1992" in stats.by_year
    assert stats.earliest_date is not None
    assert stats.latest_date is not None
    assert stats.earliest_date <= stats.latest_date


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(IndexLoadError):
        IndexStore.load(tmp_path / "does-not-exist.json")


def test_load_malformed_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(IndexLoadError):
        IndexStore.load(bad)


def test_load_schema_violation_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad-shape.json"
    bad.write_text(json.dumps({"hello": "world"}))
    with pytest.raises(IndexLoadError):
        IndexStore.load(bad)
