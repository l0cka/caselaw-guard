from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.models import Authority, CitationMatch, VerificationStatus


NEUTRAL_RE = re.compile(r"\[\d{4}\]\s+[A-Z][A-Z0-9]{1,9}\s+\d{1,5}")


class AustralianCorpusAdapter(CitationAdapter):
    name = "open-australian-legal-corpus"
    jurisdictions = frozenset({"au"})

    def __init__(self, index_path: str | Path):
        self.index_path = Path(index_path)
        self._records = self._load_index(self.index_path)

    def lookup(self, citation: CitationMatch) -> LookupResult:
        normalized = self._normalize(citation.text)
        record = self._records.get(normalized)
        if not record:
            return LookupResult(status=VerificationStatus.NOT_FOUND, normalized_citation=normalized)
        if len(record) > 1:
            return LookupResult(
                status=VerificationStatus.AMBIGUOUS,
                normalized_citation=normalized,
                candidates=[self._authority_from_record(candidate) for candidate in record],
                confidence=0.5,
            )

        authority = self._authority_from_record(record[0])
        return LookupResult(
            status=VerificationStatus.VERIFIED,
            normalized_citation=normalized,
            authority=authority,
            source_url=authority.source_url,
            confidence=1.0,
        )

    @classmethod
    def _load_index(cls, index_path: Path) -> dict[str, list[dict[str, Any]]]:
        with index_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Australian index must be a JSON array.")

        records: dict[str, list[dict[str, Any]]] = {}
        for index, record in enumerate(data):
            if not isinstance(record, dict):
                raise ValueError(f"Australian index row {index} must be an object.")
            normalized = record.get("normalized_citation")
            if not isinstance(normalized, str) or not normalized.strip():
                raise ValueError(f"Australian index row {index} is missing normalized_citation.")
            records.setdefault(cls._normalize(normalized), []).append(record)
        return records

    @staticmethod
    def _authority_from_record(record: dict[str, Any]) -> Authority:
        source_url = record.get("source_url") or record.get("url")
        return Authority(
            case_name=record.get("case_name") or record.get("citation"),
            court=record.get("court") or record.get("source"),
            date=record.get("date"),
            source_url=source_url,
            metadata={
                key: value
                for key, value in record.items()
                if key not in {"case_name", "court", "date", "source_url", "url"}
            },
        )

    @staticmethod
    def _extract_neutral(citation: str) -> str | None:
        match = NEUTRAL_RE.search(citation)
        return match.group(0) if match else None

    @staticmethod
    def _normalize(citation: str) -> str:
        return " ".join(citation.strip().split())
