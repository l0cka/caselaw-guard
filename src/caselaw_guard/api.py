from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from caselaw_guard.adapters import build_adapters
from caselaw_guard.adapters.australia import AustralianCorpusAdapter, map_australian_lookup
from caselaw_guard.adapters.base import CitationAdapter
from caselaw_guard.australia import AustralianCitationService, AustralianLookupResult
from caselaw_guard.models import Authority, VerificationStatus
from caselaw_guard.verifier import verify_text


class VerifyRequest(BaseModel):
    text: str = Field(min_length=0)


def create_app(
    *,
    adapters: Sequence[CitationAdapter] | None = None,
    au_index: str | Path | None = None,
    index_path: str | Path | None = None,
) -> FastAPI:
    if au_index is not None and index_path is not None:
        raise ValueError("Pass only one of au_index or index_path.")
    configured_index = au_index if au_index is not None else index_path
    if adapters is None:
        active_adapters = build_adapters(au_index=configured_index)
    else:
        active_adapters = list(adapters)
        if configured_index is not None:
            if any(isinstance(adapter, AustralianCorpusAdapter) for adapter in active_adapters):
                raise ValueError("Pass either an Australian adapter or an Australian index path, not both.")
            active_adapters.append(AustralianCorpusAdapter(configured_index))
    australian_adapter = next(
        (adapter for adapter in active_adapters if isinstance(adapter, AustralianCorpusAdapter)),
        None,
    )
    australian_service = australian_adapter.service if australian_adapter else None

    app = FastAPI(
        title="CaseLaw Guard",
        version="0.2.0",
        description="Fail-closed case-law citation existence verification.",
    )

    def get_australian_service() -> AustralianCitationService:
        if australian_service is None:
            raise HTTPException(status_code=503, detail={"status": "index_unavailable"})
        return australian_service

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {"status": "ok", "index_loaded": australian_service is not None}

    @app.post("/verify")
    def verify(request: VerifyRequest) -> dict[str, Any]:
        report = verify_text(request.text, adapters=active_adapters)
        return report.model_dump(by_alias=True)

    @app.get("/v1/au/citations/{citation:path}")
    def australian_lookup(
        citation: str,
        service: AustralianCitationService = Depends(get_australian_service),  # noqa: B008
    ) -> dict[str, Any]:
        return _australian_lookup_payload(service.lookup(citation))

    @app.get("/v1/au/index/metadata")
    def australian_metadata(
        service: AustralianCitationService = Depends(get_australian_service),  # noqa: B008
    ) -> dict[str, Any]:
        return service.store.metadata().model_dump(mode="json")

    @app.get("/v1/au/index/stats")
    def australian_stats(
        service: AustralianCitationService = Depends(get_australian_service),  # noqa: B008
    ) -> dict[str, Any]:
        return service.store.stats().model_dump(mode="json")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Any, error: HTTPException) -> JSONResponse:
        content = error.detail if isinstance(error.detail, dict) else {"detail": error.detail}
        return JSONResponse(status_code=error.status_code, content=content, headers=error.headers)

    return app


def _australian_lookup_payload(result: AustralianLookupResult) -> dict[str, Any]:
    mapped = map_australian_lookup(result)
    payload: dict[str, Any] = {
        "citation": result.raw_citation,
        "normalized_citation": mapped.normalized_citation,
        "status": mapped.status.value,
        "confidence": mapped.confidence,
        "candidates": [_candidate_payload(candidate) for candidate in mapped.candidates],
        "provenance": mapped.provider_metadata,
    }
    if mapped.status is VerificationStatus.VERIFIED and mapped.authority is not None:
        authority = mapped.authority
        payload.update(
            {
                "case_name": authority.case_name,
                "court": authority.court,
                "court_code": authority.metadata.get("court_code"),
                "jurisdiction": authority.metadata.get("jurisdiction"),
                "date": authority.date,
                "source_urls": authority.metadata.get("source_urls", []),
                "sources": [authority.metadata["source"]],
            }
        )
    return payload


def _candidate_payload(authority: Authority) -> dict[str, Any]:
    return {
        "case_name": authority.case_name,
        "court": authority.court,
        "court_code": authority.metadata.get("court_code"),
        "jurisdiction": authority.metadata.get("jurisdiction"),
        "date": authority.date,
        "source_urls": authority.metadata.get("source_urls", []),
    }


app = create_app()
