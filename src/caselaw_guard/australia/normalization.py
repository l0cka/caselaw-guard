"""Australian neutral-citation parsing and normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from caselaw_guard.australia.courts import canonical_court_code

_CITATION_RE = re.compile(
    r"""^\s*(?:\[(?P<bracket_year>\d{4})\]|\((?P<paren_year>\d{4})\)|(?P<bare_year>\d{4}))
    \s+(?P<court>[A-Za-z][A-Za-z0-9]*)\s+(?P<number>\d+)
    (?:\s*[, ]?\s*(?:at\s+)?\[\d+\])?\s*$""",
    re.VERBOSE | re.IGNORECASE,
)
_CITATION_SHAPE_RE = re.compile(
    r"""^\s*(?:\[\d{4}\]|\(\d{4}\)|\d{4})
    \s+[A-Za-z][A-Za-z0-9]*\s+\d+(?:\s*[, ]?\s*(?:at\s+)?\[\d+\])?\s*$""",
    re.VERBOSE | re.IGNORECASE,
)
_CITATION_INSIDE_RE = re.compile(
    r"(?:\[(?P<bracket_year>\d{4})\]|\((?P<paren_year>\d{4})\)|(?P<bare_year>\d{4}))"
    r"\s+(?P<court>[A-Za-z][A-Za-z0-9]*)\s+(?P<number>\d+)",
)
_YEAR_FLOOR = 1900


@dataclass(frozen=True)
class NormalizationResult:
    ok: bool
    normalized: str | None = None
    year: int | None = None
    court_code: str | None = None
    number: int | None = None
    raw: str = field(default="")


def _year_ceiling() -> int:
    return datetime.now().year + 1


def is_neutral_citation_shape(raw: str) -> bool:
    """Whether *raw* has neutral-citation syntax regardless of year validity."""
    return isinstance(raw, str) and _CITATION_SHAPE_RE.fullmatch(raw) is not None


def normalize_citation(raw: str) -> NormalizationResult:
    """Normalize supported Australian neutral-citation variants to one key."""
    if not isinstance(raw, str) or not raw.strip():
        return NormalizationResult(ok=False, raw=raw)
    match = _CITATION_RE.fullmatch(raw)
    if match is None:
        return NormalizationResult(ok=False, raw=raw)
    year = int(match.group("bracket_year") or match.group("paren_year") or match.group("bare_year"))
    if not _YEAR_FLOOR <= year <= _year_ceiling():
        return NormalizationResult(ok=False, raw=raw)
    court_code = canonical_court_code(match.group("court"))
    number = int(match.group("number"))
    return NormalizationResult(
        ok=True,
        normalized=f"[{year}] {court_code} {number}",
        year=year,
        court_code=court_code,
        number=number,
        raw=raw,
    )


def extract_case_name_and_citation(raw: str) -> tuple[str | None, str | None]:
    """Extract a case name and normalized citation from a corpus citation field."""
    if not isinstance(raw, str):
        return None, None
    match = _CITATION_INSIDE_RE.search(raw)
    if match is None:
        return None, None
    citation = match.group(0)
    result = normalize_citation(citation)
    if not result.ok or result.normalized is None:
        return None, None
    case_name = re.sub(r"\s+", " ", raw[: match.start()]).strip()
    return (case_name or None), result.normalized
