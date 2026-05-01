from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED_FORMAT = "unsupported_format"
    PROVIDER_ERROR = "provider_error"
    RATE_LIMITED = "rate_limited"


class CitationMatch(BaseModel):
    text: str
    start_index: int
    end_index: int
    jurisdiction_guess: str | None = None
    citation_type: str = "case"
    groups: dict[str, str] = Field(default_factory=dict)


class Authority(BaseModel):
    case_name: str | None = None
    court: str | None = None
    date: str | None = None
    docket_number: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    citation: str
    start_index: int
    end_index: int
    jurisdiction_guess: str | None
    provider: str | None
    normalized_citation: str | None
    authority: Authority | None
    source_url: str | None
    status: VerificationStatus
    confidence: float
    error_message: str | None = None


class VerificationReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pass_: bool = Field(alias="pass")
    results: list[VerificationResult]
