"""Australian neutral citation parser and normaliser.

Accepts canonical `[YYYY] COURT N` plus common variants:
  - paren-year: `(1992) HCA 23`
  - bare year: `1992 HCA 23`
  - extra whitespace, surrounding whitespace, lower-case court code
  - trailing pinpoint paragraph: `[1992] HCA 23 [10]`, `... at [10]`, `..., [10]`

Rejects everything else (including reported citations like
`(1992) 175 CLR 1`) with `ok=False`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# Year [or (year), or bare year] + COURT (alpha) + N + optional pinpoint.
_CITATION_RE = re.compile(
    r"""
    ^\s*
    (?:\[(?P<y1>\d{4})\] | \((?P<y2>\d{4})\) | (?P<y3>\d{4}))
    \s+
    (?P<court>[A-Za-z]+)
    \s+
    (?P<num>\d+)
    (?:                              # optional pinpoint
        \s*[, ]?\s*
        (?:at\s+)?
        \[\d+\]
    )?
    \s*$
    """,
    re.VERBOSE,
)

_YEAR_FLOOR = 1900


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of `normalize_citation`. `ok=False` means the rest is `None`."""

    ok: bool
    normalized: str | None = None
    year: int | None = None
    court_code: str | None = None
    number: int | None = None
    raw: str = field(default="")


def _year_ceiling() -> int:
    return datetime.now().year + 1


def normalize_citation(raw: str) -> NormalizationResult:
    """Parse and normalise an Australian neutral citation.

    Returns NormalizationResult(ok=True, normalized="[YYYY] COURT N", ...) on success,
    NormalizationResult(ok=False, raw=raw) on any rejection.
    """
    if not isinstance(raw, str) or not raw.strip():
        return NormalizationResult(ok=False, raw=raw)

    m = _CITATION_RE.match(raw)
    if m is None:
        return NormalizationResult(ok=False, raw=raw)

    year_str = m.group("y1") or m.group("y2") or m.group("y3")
    year = int(year_str)
    if year < _YEAR_FLOOR or year > _year_ceiling():
        return NormalizationResult(ok=False, raw=raw)

    court_code = m.group("court").upper()
    number = int(m.group("num"))
    normalized = f"[{year}] {court_code} {number}"

    return NormalizationResult(
        ok=True,
        normalized=normalized,
        year=year,
        court_code=court_code,
        number=number,
        raw=raw,
    )


# Match a neutral citation appearing inside a longer string (e.g. corpus citation field).
_CITATION_INSIDE_RE = re.compile(
    r"""
    (?:\[(?P<y1>\d{4})\] | \((?P<y2>\d{4})\))
    \s+
    (?P<court>[A-Za-z]+)
    \s+
    (?P<num>\d+)
    """,
    re.VERBOSE,
)


def extract_case_name_and_citation(raw: str) -> tuple[str | None, str | None]:
    """Split `Mabo v Queensland (No 2) [1992] HCA 23` into (case_name, normalised).

    Returns (None, None) if no neutral citation is found in the string.
    Pinpoint suffixes after the citation, if any, are dropped.
    """
    if not isinstance(raw, str):
        return (None, None)

    m = _CITATION_INSIDE_RE.search(raw)
    if m is None:
        return (None, None)

    year_str = m.group("y1") or m.group("y2")
    year = int(year_str)
    if year < _YEAR_FLOOR or year > _year_ceiling():
        return (None, None)

    court_code = m.group("court").upper()
    number = int(m.group("num"))
    normalized = f"[{year}] {court_code} {number}"

    case_name = raw[: m.start()].strip()
    case_name = re.sub(r"\s+", " ", case_name)
    if not case_name:
        return (None, normalized)
    return (case_name, normalized)
