from __future__ import annotations

import re

from eyecite import get_citations

from caselaw_guard.models import CitationMatch


AU_NEUTRAL_COURTS = {
    "HCA",
    "FCA",
    "FCAFC",
    "FCCA",
    "FCFCOA",
    "NSWCA",
    "NSWCCA",
    "NSWSC",
    "NSWDC",
    "NSWCAT",
    "NSWCATAP",
    "NSWCATAD",
    "NSWCATOD",
    "NSWCATEN",
    "NSWLEC",
    "NSWADT",
    "NSWADTAP",
    "NSWIRComm",
    "NSWMT",
    "VCA",
    "VSCA",
    "VSC",
    "QCA",
    "QSC",
    "QDC",
    "WASCA",
    "WASC",
    "SASC",
    "SASCA",
    "TASSC",
    "ACTSC",
    "NTSC",
    "AATA",
    "ART",
    "FWC",
}

AU_NEUTRAL_RE = re.compile(
    r"\[(?P<year>\d{4})\]\s+(?P<court>[A-Za-z][A-Za-z0-9]{1,12})\s+(?P<number>\d{1,5})"
)


def extract_citations(text: str) -> list[CitationMatch]:
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
        court = match.group("court")
        matched_text = match.group(0)
        start_index, end_index = match.span()
        key = (start_index, end_index, matched_text)
        if court not in AU_NEUTRAL_COURTS or key in seen:
            continue

        matches.append(
            CitationMatch(
                text=matched_text,
                start_index=start_index,
                end_index=end_index,
                jurisdiction_guess="au",
                groups=match.groupdict(),
            )
        )
        seen.add(key)

    return sorted(matches, key=lambda citation: (citation.start_index, citation.end_index))
