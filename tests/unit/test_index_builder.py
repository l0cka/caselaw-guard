import json
from pathlib import Path

import jsonschema

from openbench.index_builder import build_index

CORPUS = Path(__file__).parent.parent.parent / "data" / "fixtures" / "corpus-fixture.jsonl"
SCHEMA = Path(__file__).parent.parent.parent / "schemas" / "index.schema.json"


def test_builder_filters_non_decisions() -> None:
    out = build_index(CORPUS, index_version="test")
    # legislation row must not appear
    assert "Acts Interpretation Act 1901" not in json.dumps(out)


def test_builder_dedups_matching_records() -> None:
    out = build_index(CORPUS, index_version="test")
    mabo = out["entries"]["[1992] HCA 23"]
    assert isinstance(mabo, dict)
    assert sorted(mabo["source_urls"]) == [
        "https://example.org/mabo",
        "https://example.org/mabo-mirror",
    ]
    assert sorted(mabo["source_record_ids"]) == ["austlii-mabo", "hca-1992-23"]


def test_builder_emits_array_for_genuine_ambiguity() -> None:
    out = build_index(CORPUS, index_version="test")
    nswsc = out["entries"]["[2024] NSWSC 9999"]
    assert isinstance(nswsc, list)
    assert len(nswsc) == 2
    names = {e["case_name"] for e in nswsc}
    assert names == {"First Synthetic Case", "Second Synthetic Case"}


def test_builder_resolves_court_name_and_jurisdiction() -> None:
    out = build_index(CORPUS, index_version="test")
    mabo = out["entries"]["[1992] HCA 23"]
    assert mabo["court"] == "High Court of Australia"
    assert mabo["jurisdiction"] == "cth"


def test_builder_record_count_counts_distinct_citation_keys() -> None:
    out = build_index(CORPUS, index_version="test")
    # Corpus has 5 decisions: Mabo (2 records → dedup to 1 entry under 1 key),
    # NSWSC ambiguous (2 records → 2 entries under 1 key), Tasmania (1 entry under 1 key).
    # Distinct citation keys = 3. record_count = 3.
    assert out["record_count"] == 3
    assert len(out["entries"]) == 3


def test_builder_output_validates_against_schema() -> None:
    out = build_index(CORPUS, index_version="test")
    schema = json.loads(SCHEMA.read_text())
    jsonschema.validate(out, schema)


def test_builder_skips_records_with_unparseable_citation(tmp_path: Path) -> None:
    p = tmp_path / "junk.jsonl"
    p.write_text(
        '{"type":"decision","citation":"Junk no citation here","url":"https://x","date":"2020-01-01","id":"x","jurisdiction":"commonwealth"}\n'
        '{"type":"decision","citation":"Real Case [2020] HCA 1","url":"https://y","date":"2020-01-01","id":"y","jurisdiction":"commonwealth"}\n'
    )
    out = build_index(p, index_version="test")
    assert list(out["entries"].keys()) == ["[2020] HCA 1"]
