from __future__ import annotations

import os
from pathlib import Path

from caselaw_guard.adapters.australia import AustralianCorpusAdapter
from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.adapters.courtlistener import CourtListenerAdapter


def build_adapters(
    *,
    courtlistener_token: str | None = None,
    no_courtlistener: bool = False,
    au_index: str | Path | None = None,
) -> list[CitationAdapter]:
    adapters: list[CitationAdapter] = []

    if not no_courtlistener:
        token = courtlistener_token or os.getenv("CASELAW_GUARD_COURTLISTENER_TOKEN")
        if token:
            adapters.append(CourtListenerAdapter(api_token=token))

    index_path = au_index or os.getenv("CASELAW_GUARD_AU_INDEX")
    if index_path:
        adapters.append(AustralianCorpusAdapter(index_path=index_path))

    return adapters


__all__ = [
    "AustralianCorpusAdapter",
    "CitationAdapter",
    "CourtListenerAdapter",
    "LookupResult",
    "build_adapters",
]
