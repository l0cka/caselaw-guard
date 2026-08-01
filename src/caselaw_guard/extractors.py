from __future__ import annotations

import re

from eyecite import get_citations

from caselaw_guard.models import CitationMatch

AU_NEUTRAL_RE = re.compile(
    r"""(?<![A-Za-z0-9])
    (?:\[(?P<bracket_year>\d{4})\]|\((?P<paren_year>\d{4})\)|(?P<bare_year>\d{4}))
    \s+(?P<court>[A-Za-z][A-Za-z0-9]*)\s+(?P<number>\d+)
    (?:\s+(?:at\s+)?\[\d+\]|\s*,\s*\[\d+\])?
    (?![A-Za-z0-9_])
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_citations(text: str) -> list[CitationMatch]:
    if not text:
        return []

    matches: list[CitationMatch] = []
    seen: set[tuple[int, int, str]] = set()

    for citation in get_citations(text):
        matched_text = citation.matched_text()
        start_index, end_index = citation.span()
        key = (start_index, end_index, matched_text)
        if key in seen:
            continue

        groups = {key: str(value) for key, value in getattr(citation, "groups", {}).items() if value is not None}
        matches.append(
            CitationMatch(
                text=matched_text,
                start_index=start_index,
                end_index=end_index,
                jurisdiction_guess="us",
                groups=groups,
            )
        )
        seen.add(key)

    for match in AU_NEUTRAL_RE.finditer(text):
        matched_text = match.group(0)
        start_index, end_index = match.span()
        key = (start_index, end_index, matched_text)
        if key in seen:
            continue

        year = match.group("bracket_year") or match.group("paren_year") or match.group("bare_year")
        groups = {
            "year": year,
            "court": match.group("court"),
            "number": match.group("number"),
        }

        matches.append(
            CitationMatch(
                text=matched_text,
                start_index=start_index,
                end_index=end_index,
                jurisdiction_guess="au",
                groups=groups,
            )
        )
        seen.add(key)

    return sorted(matches, key=lambda citation: (citation.start_index, citation.end_index))
