from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import zstandard as zstd
from typer.testing import CliRunner

import caselaw_guard.australia.index_fetcher as index_fetcher
from caselaw_guard.australia.index_fetcher import IndexFetchError, IndexFetchResult, fetch_index
from caselaw_guard.cli import app

INDEX_VERSION = "2026-08-01"
DATASET_REVISION = "ef45e3fec41a960919a31149eee6dab9aa39f725"
SAMPLE_INDEX = Path("examples/australia_index.sample.json")
runner = CliRunner()


def _assets(index: dict[str, Any] | None = None) -> dict[str, bytes]:
    if index is None:
        payload = json.loads(SAMPLE_INDEX.read_text(encoding="utf-8"))
        payload["index_version"] = INDEX_VERSION
        payload["dataset_revision"] = DATASET_REVISION
    else:
        payload = index
    json_bytes = (json.dumps(payload, indent=2) + "\n").encode()
    compressed_bytes = zstd.ZstdCompressor().compress(json_bytes)
    json_name = f"australian-index-{INDEX_VERSION}.json"
    compressed_name = f"{json_name}.zst"
    manifest = (
        f"{hashlib.sha256(json_bytes).hexdigest()}  {json_name}\n"
        f"{hashlib.sha256(compressed_bytes).hexdigest()}  {compressed_name}\n"
    ).encode()
    return {"json": json_bytes, "compressed": compressed_bytes, "manifest": manifest}


def _transport(
    assets: dict[str, bytes],
    *,
    transform: Callable[[httpx.Request, bytes], httpx.Response] | None = None,
) -> tuple[httpx.MockTransport, list[str]]:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        body = assets["manifest"] if request.url.path.endswith(".sha256") else assets["compressed"]
        if transform is not None:
            return transform(request, body)
        return httpx.Response(200, content=body, request=request)

    return httpx.MockTransport(handler), requests


def test_fetch_downloads_fixed_assets_validates_provenance_and_replaces_atomically(tmp_path: Path) -> None:
    assets = _assets()
    transport, requests = _transport(assets)
    output = tmp_path / "australia-index.json"

    result = fetch_index(INDEX_VERSION, output, transport=transport)

    assert result == IndexFetchResult(
        output_path=output.resolve(),
        index_version=INDEX_VERSION,
        dataset_revision=DATASET_REVISION,
        record_count=1,
        license="CC-BY-4.0",
        attribution=(
            "Open Australian Legal Corpus by Isaacus, CC-BY-4.0, modified by CaseLaw "
            "Guard (metadata extraction, normalisation and deduplication)."
        ),
        compressed_sha256=hashlib.sha256(assets["compressed"]).hexdigest(),
        json_sha256=hashlib.sha256(assets["json"]).hexdigest(),
    )
    assert output.read_bytes() == assets["json"]
    assert requests == [
        "https://github.com/l0cka/caselaw-guard/releases/download/australian-index-2026-08-01/australian-index-2026-08-01.json.zst",
        "https://github.com/l0cka/caselaw-guard/releases/download/australian-index-2026-08-01/australian-index-2026-08-01.json.sha256",
    ]
    assert list(tmp_path.glob(".*.part")) == []


def test_fetch_rejects_invalid_versions_before_network(tmp_path: Path) -> None:
    transport, requests = _transport(_assets())

    for version in ("latest", "2026-8-01", "2026-02-30", "https://example.test/index"):
        with pytest.raises(IndexFetchError, match="YYYY-MM-DD"):
            fetch_index(version, tmp_path / "index.json", transport=transport)

    assert requests == []


@pytest.mark.parametrize("asset", ["compressed", "manifest"])
def test_fetch_preserves_existing_output_on_http_failure(tmp_path: Path, asset: str) -> None:
    output = tmp_path / "index.json"
    previous = b"previous valid index"
    output.write_bytes(previous)

    def fail_asset(request: httpx.Request, body: bytes) -> httpx.Response:
        if (asset == "compressed" and request.url.path.endswith(".zst")) or (
            asset == "manifest" and request.url.path.endswith(".sha256")
        ):
            return httpx.Response(404, request=request)
        return httpx.Response(200, content=body, request=request)

    transport, _ = _transport(_assets(), transform=fail_asset)
    with pytest.raises(IndexFetchError, match="HTTP 404"):
        fetch_index(INDEX_VERSION, output, force=True, transport=transport)

    assert output.read_bytes() == previous


def test_fetch_refuses_existing_output_without_force(tmp_path: Path) -> None:
    output = tmp_path / "index.json"
    output.write_bytes(b"previous valid index")
    transport, requests = _transport(_assets())

    with pytest.raises(IndexFetchError, match="already exists"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert output.read_bytes() == b"previous valid index"
    assert requests == []


def test_fetch_refuses_symbolic_link_even_with_force(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"target contents")
    output = tmp_path / "index.json"
    output.symlink_to(target)
    transport, requests = _transport(_assets())

    with pytest.raises(IndexFetchError, match="symbolic link"):
        fetch_index(INDEX_VERSION, output, force=True, transport=transport)

    assert output.is_symlink()
    assert target.read_bytes() == b"target contents"
    assert requests == []


def test_fetch_force_replaces_existing_output_after_all_checks(tmp_path: Path) -> None:
    output = tmp_path / "index.json"
    output.write_bytes(b"previous valid index")
    transport, _ = _transport(_assets())

    fetch_index(INDEX_VERSION, output, force=True, transport=transport)

    assert json.loads(output.read_text(encoding="utf-8"))["index_version"] == INDEX_VERSION
    assert list(tmp_path.glob(".*.part")) == []


def test_fetch_rejects_manifest_mismatch_without_installing(tmp_path: Path) -> None:
    assets = _assets()
    assets["manifest"] = assets["manifest"].replace(b"a", b"b", 1)
    transport, _ = _transport(assets)
    output = tmp_path / "index.json"

    with pytest.raises(IndexFetchError, match="checksum manifest"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert not output.exists()


def test_fetch_rejects_compressed_digest_mismatch_without_installing(tmp_path: Path) -> None:
    assets = _assets()
    digest, filename = assets["manifest"].decode().splitlines()[1].split("  ")
    assets["manifest"] = assets["manifest"].replace(digest.encode(), ("0" * 64).encode())
    assert filename.endswith(".json.zst")
    transport, _ = _transport(assets)
    output = tmp_path / "index.json"

    with pytest.raises(IndexFetchError, match="compressed asset digest"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert not output.exists()


def test_fetch_rejects_invalid_compressed_stream(tmp_path: Path) -> None:
    assets = _assets()
    assets["compressed"] = b"truncated zstandard stream"
    compressed_name = f"australian-index-{INDEX_VERSION}.json.zst"
    lines = assets["manifest"].decode().splitlines()
    lines[1] = f"{hashlib.sha256(assets['compressed']).hexdigest()}  {compressed_name}"
    assets["manifest"] = ("\n".join(lines) + "\n").encode()
    transport, _ = _transport(assets)
    output = tmp_path / "index.json"

    with pytest.raises(IndexFetchError, match="decompress"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert not output.exists()


def test_fetch_rejects_malformed_json_and_schema_without_installing(tmp_path: Path) -> None:
    for payload in (b"not json", json.dumps({"index_version": INDEX_VERSION}).encode()):
        assets = _assets()
        assets["json"] = payload
        assets["compressed"] = zstd.ZstdCompressor().compress(payload)
        lines = assets["manifest"].decode().splitlines()
        lines[0] = f"{hashlib.sha256(payload).hexdigest()}  australian-index-{INDEX_VERSION}.json"
        lines[1] = f"{hashlib.sha256(assets['compressed']).hexdigest()}  australian-index-{INDEX_VERSION}.json.zst"
        assets["manifest"] = ("\n".join(lines) + "\n").encode()
        transport, _ = _transport(assets)
        output = tmp_path / f"index-{len(payload)}.json"

        with pytest.raises(IndexFetchError, match="canonical index"):
            fetch_index(INDEX_VERSION, output, transport=transport)

        assert not output.exists()


@pytest.mark.parametrize(
    "field, value", [("index_version", "2025-01-01"), ("license", "MIT"), ("attribution", "wrong")]
)
def test_fetch_rejects_untrusted_canonical_metadata(tmp_path: Path, field: str, value: str) -> None:
    index = json.loads(SAMPLE_INDEX.read_text(encoding="utf-8"))
    index["index_version"] = INDEX_VERSION
    index["dataset_revision"] = DATASET_REVISION
    index[field] = value
    assets = _assets(index)
    transport, _ = _transport(assets)
    output = tmp_path / "index.json"

    with pytest.raises(IndexFetchError, match="metadata"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert not output.exists()


def test_fetch_enforces_compressed_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_fetcher, "MAX_COMPRESSED_BYTES", 1)
    transport, _ = _transport(_assets())

    with pytest.raises(IndexFetchError, match="compressed asset exceeds"):
        fetch_index(INDEX_VERSION, tmp_path / "index.json", transport=transport)


def test_fetch_enforces_decompressed_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_fetcher, "MAX_DECOMPRESSED_BYTES", 1)
    transport, _ = _transport(_assets())

    with pytest.raises(IndexFetchError, match="decompressed index exceeds"):
        fetch_index(INDEX_VERSION, tmp_path / "index.json", transport=transport)


def test_fetch_wraps_network_timeouts_and_cleans_temporary_files(tmp_path: Path) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    transport = httpx.MockTransport(timeout)
    output = tmp_path / "index.json"

    with pytest.raises(IndexFetchError, match="timed out"):
        fetch_index(INDEX_VERSION, output, transport=transport)

    assert not output.exists()
    assert list(tmp_path.glob(".*.part")) == []


def test_cli_fetch_prints_json_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "index.json"
    expected = IndexFetchResult(
        output_path=output.resolve(),
        index_version=INDEX_VERSION,
        dataset_revision=DATASET_REVISION,
        record_count=1,
        license="CC-BY-4.0",
        attribution="canonical attribution",
        compressed_sha256="a" * 64,
        json_sha256="b" * 64,
    )
    monkeypatch.setattr("caselaw_guard.cli.fetch_index", lambda *args, **kwargs: expected)

    result = runner.invoke(app, ["au-index", "fetch", INDEX_VERSION, "--output", str(output)])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "output_path": str(output.resolve()),
        "index_version": INDEX_VERSION,
        "dataset_revision": DATASET_REVISION,
        "record_count": 1,
        "license": "CC-BY-4.0",
        "attribution": "canonical attribution",
        "compressed_sha256": "a" * 64,
        "json_sha256": "b" * 64,
    }
