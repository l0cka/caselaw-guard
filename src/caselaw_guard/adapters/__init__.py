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
    cache_path: str | Path | None = None,
    cache_ttl_days: int | None = None,
) -> list[CitationAdapter]:
    adapters: list[CitationAdapter] = []

    if not no_courtlistener:
        token = courtlistener_token or os.getenv("CASELAW_GUARD_COURTLISTENER_TOKEN")
        if token:
            adapters.append(
                CourtListenerAdapter(
                    api_token=token,
                    cache_path=cache_path or os.getenv("CASELAW_GUARD_CACHE"),
                    cache_ttl_days=(
                        cache_ttl_days if cache_ttl_days is not None else _env_int("CASELAW_GUARD_CACHE_TTL_DAYS", 30)
                    ),
                )
            )

    index_path = au_index or os.getenv("CASELAW_GUARD_AU_INDEX")
    if index_path:
        adapters.append(AustralianCorpusAdapter(index_path=index_path))

    return adapters


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


__all__ = [
    "AustralianCorpusAdapter",
    "CitationAdapter",
    "CourtListenerAdapter",
    "LookupResult",
    "build_adapters",
]
