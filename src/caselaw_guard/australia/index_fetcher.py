"""Fetch and atomically install a verified Australian citation index."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

import httpx
import zstandard as zstd
from pydantic import ValidationError

from caselaw_guard.australia.models import ATTRIBUTION, IndexFile

RELEASE_URL_TEMPLATE: Final = (
    "https://github.com/l0cka/caselaw-guard/releases/download/australian-index-{version}/australian-index-{version}"
)
MAX_COMPRESSED_BYTES = 256 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 1024 * 1024 * 1024
MAX_CHECKSUM_MANIFEST_BYTES = 1024 * 1024
CHUNK_SIZE = 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 30.0
TOTAL_TIMEOUT_SECONDS = 300.0
_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class IndexFetchError(RuntimeError):
    """Raised when an index cannot be downloaded, trusted, or installed."""


@dataclass(frozen=True)
class IndexFetchResult:
    """Provenance and integrity details for an installed index."""

    output_path: Path
    index_version: str
    dataset_revision: str
    record_count: int
    license: str
    attribution: str
    compressed_sha256: str
    json_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "output_path": str(self.output_path),
            "index_version": self.index_version,
            "dataset_revision": self.dataset_revision,
            "record_count": self.record_count,
            "license": self.license,
            "attribution": self.attribution,
            "compressed_sha256": self.compressed_sha256,
            "json_sha256": self.json_sha256,
        }


def fetch_index(
    version: str,
    output: str | Path,
    *,
    force: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> IndexFetchResult:
    """Fetch a fixed release asset and atomically install its canonical JSON index."""
    _validate_version(version)
    output_path = Path(output)
    _check_output_path(output_path, force=force)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise IndexFetchError(f"could not prepare output directory {output_path.parent}: {error}") from error

    json_name = f"australian-index-{version}.json"
    compressed_name = f"{json_name}.zst"
    compressed_url = f"{RELEASE_URL_TEMPLATE.format(version=version)}.json.zst"
    manifest_url = f"{RELEASE_URL_TEMPLATE.format(version=version)}.json.sha256"
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
    temporary_paths: list[Path] = []

    try:
        compressed_path = _temporary_path(output_path.parent, output_path.name, temporary_paths)
        manifest_path = _temporary_path(output_path.parent, output_path.name, temporary_paths)
        json_path = _temporary_path(output_path.parent, output_path.name, temporary_paths)
        timeout = httpx.Timeout(
            READ_TIMEOUT_SECONDS,
            connect=CONNECT_TIMEOUT_SECONDS,
            read=READ_TIMEOUT_SECONDS,
        )
        with httpx.Client(transport=transport, timeout=timeout, follow_redirects=True) as client:
            compressed_sha256 = _download_asset(
                client,
                compressed_url,
                compressed_path,
                max_bytes=MAX_COMPRESSED_BYTES,
                deadline=deadline,
                label="compressed asset",
            )
            _download_asset(
                client,
                manifest_url,
                manifest_path,
                max_bytes=MAX_CHECKSUM_MANIFEST_BYTES,
                deadline=deadline,
                label="checksum manifest",
            )

        expected_digests = _read_checksum_manifest(manifest_path, json_name, compressed_name)
        if compressed_sha256 != expected_digests[compressed_name]:
            raise IndexFetchError("compressed asset digest does not match the checksum manifest")

        json_sha256 = _decompress_asset(
            compressed_path,
            json_path,
            deadline=deadline,
        )
        if json_sha256 != expected_digests[json_name]:
            raise IndexFetchError("JSON asset digest does not match the checksum manifest")

        index = _load_canonical_index(json_path)
        _validate_metadata(index, version)
        _check_output_path(output_path, force=force)
        try:
            os.replace(json_path, output_path)
        except OSError as error:
            raise IndexFetchError(f"could not atomically install {output_path}: {error}") from error

        return IndexFetchResult(
            output_path=output_path.resolve(),
            index_version=index.index_version,
            dataset_revision=index.dataset_revision,
            record_count=index.record_count,
            license=index.license,
            attribution=index.attribution,
            compressed_sha256=compressed_sha256,
            json_sha256=json_sha256,
        )
    except IndexFetchError:
        raise
    except OSError as error:
        raise IndexFetchError(f"index fetch failed: {error}") from error
    finally:
        for temporary_path in temporary_paths:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def _validate_version(version: str) -> None:
    if not _VERSION_PATTERN.fullmatch(version):
        raise IndexFetchError("index version must use YYYY-MM-DD format")
    try:
        date.fromisoformat(version)
    except ValueError as error:
        raise IndexFetchError("index version must be a valid YYYY-MM-DD date") from error


def _check_output_path(output: Path, *, force: bool) -> None:
    if output.is_symlink():
        raise IndexFetchError(f"refusing to replace symbolic link: {output}")
    if output.exists() and not force:
        raise IndexFetchError(f"output already exists; pass --force to replace it: {output}")
    if output.exists() and not output.is_file():
        raise IndexFetchError(f"output is not a regular file: {output}")


def _temporary_path(directory: Path, output_name: str, temporary_paths: list[Path]) -> Path:
    try:
        with tempfile.NamedTemporaryFile(
            dir=directory, prefix=f".{output_name}.", suffix=".part", delete=False
        ) as handle:
            path = Path(handle.name)
    except OSError as error:
        raise IndexFetchError(f"could not create temporary file in {directory}: {error}") from error
    temporary_paths.append(path)
    return path


def _download_asset(
    client: httpx.Client,
    url: str,
    destination: Path,
    *,
    max_bytes: int,
    deadline: float,
    label: str,
) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    if int(content_length) > max_bytes:
                        raise IndexFetchError(f"{label} exceeds the {max_bytes}-byte limit")
                except ValueError:
                    pass
            with destination.open("wb") as output:
                for chunk in response.iter_bytes(CHUNK_SIZE):
                    _check_deadline(deadline)
                    total += len(chunk)
                    if total > max_bytes:
                        raise IndexFetchError(f"{label} exceeds the {max_bytes}-byte limit")
                    output.write(chunk)
                    digest.update(chunk)
    except IndexFetchError:
        raise
    except httpx.TimeoutException as error:
        raise IndexFetchError(f"download timed out for {url}") from error
    except httpx.HTTPStatusError as error:
        raise IndexFetchError(f"download failed for {url}: HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise IndexFetchError(f"download failed for {url}: {error}") from error
    except OSError as error:
        raise IndexFetchError(f"could not write downloaded {label}: {error}") from error
    return digest.hexdigest()


def _read_checksum_manifest(path: Path, json_name: str, compressed_name: str) -> dict[str, str]:
    try:
        contents = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise IndexFetchError(f"checksum manifest is unreadable: {error}") from error

    entries: dict[str, str] = {}
    for line_number, line in enumerate(contents.splitlines(), start=1):
        parts = line.split()
        if len(parts) != 2 or not _SHA256_PATTERN.fullmatch(parts[0]):
            raise IndexFetchError(f"checksum manifest line {line_number} is malformed")
        filename = parts[1].removeprefix("*")
        if filename in entries and entries[filename] != parts[0].lower():
            raise IndexFetchError(f"checksum manifest contains conflicting entries for {filename}")
        entries[filename] = parts[0].lower()

    required = {json_name, compressed_name}
    missing = sorted(required - entries.keys())
    if missing:
        raise IndexFetchError(f"checksum manifest is missing entries: {', '.join(missing)}")
    return {name: entries[name] for name in required}


def _decompress_asset(compressed_path: Path, json_path: Path, *, deadline: float) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with (
            compressed_path.open("rb") as compressed,
            zstd.ZstdDecompressor().stream_reader(compressed) as reader,
            json_path.open("wb") as output,
        ):
            while True:
                _check_deadline(deadline)
                chunk = reader.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DECOMPRESSED_BYTES:
                    raise IndexFetchError(f"decompressed index exceeds the {MAX_DECOMPRESSED_BYTES}-byte limit")
                output.write(chunk)
                digest.update(chunk)
    except IndexFetchError:
        raise
    except (OSError, zstd.ZstdError) as error:
        raise IndexFetchError(f"could not decompress compressed index: {error}") from error
    return digest.hexdigest()


def _load_canonical_index(path: Path) -> IndexFile:
    try:
        with path.open(encoding="utf-8") as source:
            raw = json.load(source)
        return IndexFile.model_validate(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        raise IndexFetchError(f"downloaded file is not a valid canonical index: {error}") from error


def _validate_metadata(index: IndexFile, version: str) -> None:
    if index.index_version != version:
        raise IndexFetchError(
            f"downloaded index metadata does not match requested version {version}: {index.index_version}"
        )
    if index.license != "CC-BY-4.0":
        raise IndexFetchError(f"downloaded index metadata has an unsupported license: {index.license}")
    if index.attribution != ATTRIBUTION:
        raise IndexFetchError("downloaded index metadata has non-canonical attribution")


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise IndexFetchError("index fetch exceeded the total timeout")
