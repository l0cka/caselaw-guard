from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
import zstandard as zstd

from caselaw_guard.australia.models import ATTRIBUTION

_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "build_release_index.py"
_SPEC = importlib.util.spec_from_file_location("build_release_index", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
build_release_index = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = build_release_index
_SPEC.loader.exec_module(build_release_index)


def test_sample_index_is_canonical_and_schema_valid() -> None:
    sample = Path("examples/australia_index.sample.json")
    build_release_index._validate(sample)
    payload = json.loads(sample.read_text(encoding="utf-8"))
    assert payload["dataset_revision"] == "unknown"
    assert payload["attribution"] == ATTRIBUTION
    assert payload["record_count"] == len(payload["entries"])


def test_local_corpus_build_is_offline_and_records_supplied_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "australian-index-test.json"
    corpus.write_text(
        json.dumps(
            {
                "type": "decision",
                "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                "url": "https://example.test/mabo",
                "id": "mabo",
                "date": "1992-06-03",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_release_index, "_dataset_revision", _network_must_not_run)

    build_release_index.main(
        [
            "--corpus",
            str(corpus),
            "--output",
            str(output),
            "--index-version",
            "test-1",
            "--dataset-revision",
            "abc123",
        ]
    )

    index = json.loads(output.read_text(encoding="utf-8"))
    compressed = output.with_suffix(".json.zst")
    checksums = output.with_suffix(".json.sha256")
    assert index["dataset_revision"] == "abc123"
    assert index["attribution"] == ATTRIBUTION
    assert zstd.ZstdDecompressor().decompress(compressed.read_bytes()) == output.read_bytes()
    assert checksums.read_text(encoding="utf-8").splitlines() == [
        f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}",
        f"{hashlib.sha256(compressed.read_bytes()).hexdigest()}  {compressed.name}",
    ]


def test_local_corpus_without_revision_records_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "index.json"
    corpus.write_text("", encoding="utf-8")
    monkeypatch.setattr(build_release_index, "_dataset_revision", _network_must_not_run)

    build_release_index.main(["--corpus", str(corpus), "--output", str(output), "--index-version", "test-unknown"])

    assert json.loads(output.read_text(encoding="utf-8"))["dataset_revision"] == "unknown"


def test_remote_build_streams_the_corpus_split_at_the_supplied_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_load_dataset(dataset: str, **kwargs: object) -> list[dict[str, object]]:
        calls.append((dataset, kwargs))
        return [
            {
                "type": "decision",
                "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                "url": "https://example.test/mabo",
                "id": "mabo",
                "date": "1992-06-03T00:00:00Z",
                "jurisdiction": "cth",
            },
            {"type": "legislation", "citation": "Privacy Act 1988 (Cth)"},
        ]

    datasets = ModuleType("datasets")
    datasets.load_dataset = fake_load_dataset  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "datasets", datasets)
    output = tmp_path / "corpus.jsonl"

    count = build_release_index._stream_decisions_to_jsonl(output, revision="abc123")

    assert calls == [
        (
            build_release_index.DATASET,
            {"split": "corpus", "streaming": True, "revision": "abc123"},
        )
    ]
    assert count == 1
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "type": "decision",
        "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
        "url": "https://example.test/mabo",
        "date": "1992-06-03",
        "jurisdiction": "cth",
        "id": "mabo",
    }


def test_coverage_report_is_added_to_checksum_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "australian-index-test.json"
    report = tmp_path / "australian-index-test.verification.json"
    baseline = tmp_path / "baseline.json"
    corpus.write_text(
        json.dumps(
            {
                "type": "decision",
                "citation": "Mabo v Queensland (No 2) [1992] HCA 23",
                "url": "https://example.test/mabo",
                "id": "mabo",
                "date": "1992-06-03",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    baseline.write_text("{}", encoding="utf-8")

    def fake_coverage_gate(index_path: Path, baseline_path: Path, report_path: Path) -> None:
        assert index_path == output
        assert baseline_path == baseline
        report_path.write_text(json.dumps({"coverage": "passed"}), encoding="utf-8")

    monkeypatch.setattr(build_release_index, "_run_coverage_gate", fake_coverage_gate)

    build_release_index.main(
        [
            "--corpus",
            str(corpus),
            "--output",
            str(output),
            "--index-version",
            "test-coverage",
            "--dataset-revision",
            "abc123",
            "--coverage-baseline",
            str(baseline),
            "--verification-report",
            str(report),
        ]
    )

    compressed = output.with_suffix(".json.zst")
    checksum_lines = output.with_suffix(".json.sha256").read_text(encoding="utf-8").splitlines()
    assert checksum_lines == [
        f"{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}",
        f"{hashlib.sha256(compressed.read_bytes()).hexdigest()}  {compressed.name}",
        f"{hashlib.sha256(report.read_bytes()).hexdigest()}  {report.name}",
    ]


def test_coverage_gate_failure_does_not_write_checksum_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = tmp_path / "corpus.jsonl"
    output = tmp_path / "australian-index-test.json"
    baseline = tmp_path / "baseline.json"
    corpus.write_text("", encoding="utf-8")
    baseline.write_text("{}", encoding="utf-8")

    def fail_coverage_gate(_index_path: Path, _baseline_path: Path, _report_path: Path) -> None:
        raise ValueError("coverage regression")

    monkeypatch.setattr(build_release_index, "_run_coverage_gate", fail_coverage_gate)

    with pytest.raises(ValueError, match="coverage regression"):
        build_release_index.main(
            [
                "--corpus",
                str(corpus),
                "--output",
                str(output),
                "--index-version",
                "test-failure",
                "--coverage-baseline",
                str(baseline),
            ]
        )

    assert output.is_file()
    assert output.with_suffix(".json.zst").is_file()
    assert not output.with_suffix(".json.sha256").exists()


def _network_must_not_run() -> str:
    raise AssertionError("offline local-corpus builds must not resolve the remote dataset")
