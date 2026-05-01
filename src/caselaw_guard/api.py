from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI
from pydantic import BaseModel, Field

from caselaw_guard.adapters.base import CitationAdapter
from caselaw_guard.verifier import verify_text


class VerifyRequest(BaseModel):
    text: str = Field(min_length=0)


def create_app(*, adapters: Sequence[CitationAdapter] | None = None) -> FastAPI:
    app = FastAPI(
        title="CaseLaw Guard",
        version="0.1.0",
        description="Fail-closed case-law citation existence verification.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/verify")
    def verify(request: VerifyRequest) -> dict:
        report = verify_text(request.text, adapters=adapters)
        return report.model_dump(by_alias=True)

    return app


app = create_app()
