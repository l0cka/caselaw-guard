"""FastAPI application exposing the openbench citation lookup API."""

import os
import re
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse

from openbench import __version__
from openbench.index_store import IndexLoadError, IndexStore
from openbench.models import (
    ATTRIBUTION,
    Candidate,
    HealthResponse,
    IndexEntry,
    IndexMetadata,
    IndexStats,
    LookupResponse,
    Provenance,
    Status,
)
from openbench.normalization import normalize_citation

INDEX_ENV = "AUS_CASE_INDEX"

# Loose pattern: matches citations with valid structure but ignores year range.
# Used to distinguish "valid format, not in index" from "unrecognised format".
_CITATION_SHAPE_RE = re.compile(
    r"""
    ^\s*
    (?:\[\d{4}\] | \(\d{4}\) | \d{4})
    \s+
    [A-Za-z]+
    \s+
    \d+
    (?:\s*[, ]?\s*(?:at\s+)?\[\d+\])?
    \s*$
    """,
    re.VERBOSE,
)


def _try_load(index_path: Path | str | None) -> IndexStore | None:
    if index_path is None:
        return None
    try:
        return IndexStore.load(index_path)
    except IndexLoadError:
        return None


def create_app(*, index_path: Path | str | None = None) -> FastAPI:
    """Create a FastAPI app, optionally pre-loading an index file.

    If `index_path` is None, the app starts in `index_unavailable` mode and
    `/health` reports `index_loaded: false`. Lookup/metadata/stats return 503.
    """
    if index_path is None:
        index_path = os.environ.get(INDEX_ENV)
    store: IndexStore | None = _try_load(index_path)

    app = FastAPI(
        title="openbench",
        version=__version__,
        description=(
            "Open Australian case-law citation lookup. Verifies citation presence "
            "in an open index. Not an official court or government API; not legal advice."
        ),
    )

    def get_store() -> IndexStore:
        if store is None:
            raise HTTPException(
                status_code=503,
                detail={"status": Status.index_unavailable.value},
            )
        return store

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", index_loaded=store is not None)

    @app.get("/v1/au/citations/{citation:path}", response_model=LookupResponse)
    def lookup(
        citation: Annotated[str, PathParam(...)],
        current_store: Annotated[IndexStore, Depends(get_store)],
    ) -> LookupResponse:
        result = normalize_citation(citation)
        if not result.ok or result.normalized is None:
            # If the citation has valid neutral-citation shape but a year outside
            # the normalization ceiling (e.g. [2099] HCA 999), treat it as
            # not_found rather than unsupported_format.
            if _CITATION_SHAPE_RE.match(citation):
                return LookupResponse(
                    citation=citation,
                    status=Status.not_found,
                    confidence=0.0,
                    candidates=[],
                )
            return LookupResponse(
                citation=citation,
                status=Status.unsupported_format,
                confidence=0.0,
                candidates=[],
            )

        entries: list[IndexEntry] = current_store.lookup(result.normalized)
        provenance = Provenance(
            index_version=current_store.index_version,
            source=current_store.source,
            license=current_store.license,
            dataset="isaacus/open-australian-legal-corpus",
            attribution=ATTRIBUTION,
        )
        if not entries:
            return LookupResponse(
                citation=citation,
                normalized_citation=result.normalized,
                status=Status.not_found,
                confidence=0.0,
                candidates=[],
                provenance=provenance,
            )
        if len(entries) == 1:
            e = entries[0]
            return LookupResponse(
                citation=citation,
                normalized_citation=result.normalized,
                status=Status.verified,
                case_name=e.case_name,
                court=e.court,
                court_code=e.court_code,
                jurisdiction=e.jurisdiction,
                date=e.date,
                source_urls=list(e.source_urls),
                sources=[e.source],
                confidence=1.0,
                candidates=[],
                provenance=provenance,
            )
        # ambiguous
        candidates = [
            Candidate(
                case_name=e.case_name,
                court=e.court,
                court_code=e.court_code,
                jurisdiction=e.jurisdiction,
                date=e.date,
                source_urls=list(e.source_urls),
            )
            for e in entries
        ]
        return LookupResponse(
            citation=citation,
            normalized_citation=result.normalized,
            status=Status.ambiguous,
            confidence=0.5,
            candidates=candidates,
            provenance=provenance,
        )

    @app.get("/v1/au/index/metadata", response_model=IndexMetadata)
    def metadata(current_store: Annotated[IndexStore, Depends(get_store)]) -> IndexMetadata:
        return current_store.metadata()

    @app.get("/v1/au/index/stats", response_model=IndexStats)
    def stats(current_store: Annotated[IndexStore, Depends(get_store)]) -> IndexStats:
        return current_store.stats()

    @app.exception_handler(HTTPException)
    async def _http_exc(  # type: ignore[no-untyped-def]
        _req,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return app
