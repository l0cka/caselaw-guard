from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from caselaw_guard.adapters.base import CitationAdapter, LookupResult
from caselaw_guard.models import Authority, CitationMatch, VerificationStatus


CITATION_RE = re.compile(r"^(?P<volume>\d+)\s+(?P<reporter>.+?)\s+(?P<page>\d+[A-Za-z]?)$")


class CourtListenerAdapter(CitationAdapter):
    name = "courtlistener"
    jurisdictions = frozenset({"us"})

    def __init__(
        self,
        api_token: str | None = None,
        *,
        base_url: str = "https://www.courtlistener.com",
        client: httpx.Client | None = None,
        timeout: float = 15.0,
        cache_path: str | Path | None = None,
        cache_ttl_days: int = 30,
    ):
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache_ttl = timedelta(days=cache_ttl_days)

    def lookup(self, citation: CitationMatch) -> LookupResult:
        data = self._citation_payload(citation)
        cache_key = self._cache_key(data)
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        headers = {"Authorization": f"Token {self.api_token}"} if self.api_token else {}

        try:
            response = self.client.post(
                f"{self.base_url}/api/rest/v4/citation-lookup/",
                headers=headers,
                data=data,
            )
        except httpx.HTTPError as error:
            return LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message=str(error),
            )

        if response.status_code == 429:
            result = LookupResult(
                status=VerificationStatus.RATE_LIMITED,
                normalized_citation=citation.text,
                error_message="CourtListener rate limit exceeded.",
                provider_metadata=self._json_object(response),
            )
            return result
        if response.status_code >= 400:
            result = LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message=f"CourtListener returned HTTP {response.status_code}.",
            )
            return result

        try:
            payload = response.json()
        except ValueError:
            return LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message="CourtListener returned non-JSON content.",
            )

        if not isinstance(payload, list):
            return LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message="CourtListener returned an unexpected JSON shape.",
            )
        if not payload:
            result = LookupResult(status=VerificationStatus.NOT_FOUND, normalized_citation=citation.text)
            self._cache_set(cache_key, result)
            return result

        result = self._lookup_result_from_entry(payload[0], citation.text)
        self._cache_set(cache_key, result)
        return result

    def _citation_payload(self, citation: CitationMatch) -> dict[str, str]:
        if {"volume", "reporter", "page"} <= set(citation.groups):
            return {
                "volume": citation.groups["volume"],
                "reporter": citation.groups["reporter"],
                "page": citation.groups["page"],
            }

        match = CITATION_RE.match(citation.text)
        if match:
            return match.groupdict()

        return {"text": citation.text}

    def _lookup_result_from_entry(self, entry: dict[str, Any], original_citation: str) -> LookupResult:
        normalized = self._normalized_citation(entry, original_citation)
        status = self._status_from_code(entry.get("status"))
        clusters = entry.get("clusters") or []
        candidates = [self._authority_from_cluster(cluster) for cluster in clusters]
        authority = candidates[0] if status == VerificationStatus.VERIFIED and candidates else None
        source_url = authority.source_url if authority else None

        return LookupResult(
            status=status,
            normalized_citation=normalized,
            authority=authority,
            source_url=source_url,
            confidence=self._confidence(status),
            error_message=entry.get("error_message") or None,
            candidates=candidates if status == VerificationStatus.AMBIGUOUS else [],
            provider_metadata={
                "normalized_citations": entry.get("normalized_citations") or [],
            },
        )

    def _authority_from_cluster(self, cluster: dict[str, Any]) -> Authority:
        absolute_url = cluster.get("absolute_url") or cluster.get("resource_uri")
        source_url = None
        if absolute_url:
            source_url = absolute_url if absolute_url.startswith("http") else f"{self.base_url}{absolute_url}"

        return Authority(
            case_name=cluster.get("case_name") or cluster.get("case_name_full"),
            court=self._court_name(cluster),
            date=cluster.get("date_filed") or cluster.get("date_created"),
            docket_number=cluster.get("docket_id"),
            source_url=source_url,
            metadata={
                key: value
                for key, value in cluster.items()
                if key
                not in {
                    "case_name",
                    "case_name_full",
                    "court",
                    "date_filed",
                    "date_created",
                    "docket_id",
                    "absolute_url",
                    "resource_uri",
                }
            },
        )

    @staticmethod
    def _court_name(cluster: dict[str, Any]) -> str | None:
        court = cluster.get("court")
        if isinstance(court, dict):
            return court.get("full_name") or court.get("id")
        return court

    @staticmethod
    def _normalized_citation(entry: dict[str, Any], original_citation: str) -> str:
        normalized = entry.get("normalized_citations") or []
        return normalized[0] if normalized else entry.get("citation", original_citation)

    @staticmethod
    def _status_from_code(status_code: int | str | None) -> VerificationStatus:
        try:
            code = int(status_code)
        except (TypeError, ValueError):
            return VerificationStatus.PROVIDER_ERROR

        return {
            200: VerificationStatus.VERIFIED,
            300: VerificationStatus.AMBIGUOUS,
            400: VerificationStatus.UNSUPPORTED_FORMAT,
            404: VerificationStatus.NOT_FOUND,
            429: VerificationStatus.RATE_LIMITED,
        }.get(code, VerificationStatus.PROVIDER_ERROR)

    @staticmethod
    def _confidence(status: VerificationStatus) -> float:
        if status == VerificationStatus.VERIFIED:
            return 1.0
        if status == VerificationStatus.AMBIGUOUS:
            return 0.5
        return 0.0

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _cache_key(data: dict[str, str]) -> str:
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cache_get(self, cache_key: str) -> LookupResult | None:
        if not self.cache_path or self.cache_ttl <= timedelta(0):
            return None

        cache = self._read_cache()
        entry = cache.get(cache_key)
        if not isinstance(entry, dict):
            return None

        cached_at = self._parse_cached_at(entry.get("cached_at"))
        if not cached_at or datetime.now(timezone.utc) - cached_at >= self.cache_ttl:
            return None

        result = entry.get("result")
        if not isinstance(result, dict):
            return None
        return self._lookup_result_from_cache(result)

    def _cache_set(self, cache_key: str, result: LookupResult) -> None:
        if not self.cache_path or result.status in {VerificationStatus.PROVIDER_ERROR, VerificationStatus.RATE_LIMITED}:
            return

        cache = self._read_cache()
        cache[cache_key] = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "result": self._lookup_result_to_cache(result),
        }
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _read_cache(self) -> dict[str, Any]:
        if not self.cache_path or not self.cache_path.exists():
            return {}
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _parse_cached_at(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _lookup_result_to_cache(result: LookupResult) -> dict[str, Any]:
        return {
            "status": result.status.value,
            "normalized_citation": result.normalized_citation,
            "authority": result.authority.model_dump() if result.authority else None,
            "source_url": result.source_url,
            "confidence": result.confidence,
            "error_message": result.error_message,
            "candidates": [candidate.model_dump() for candidate in result.candidates],
            "provider_metadata": result.provider_metadata,
        }

    @staticmethod
    def _lookup_result_from_cache(data: dict[str, Any]) -> LookupResult | None:
        try:
            status = VerificationStatus(data["status"])
        except (KeyError, ValueError):
            return None

        authority = data.get("authority")
        candidates = data.get("candidates") or []
        return LookupResult(
            status=status,
            normalized_citation=data.get("normalized_citation"),
            authority=Authority.model_validate(authority) if isinstance(authority, dict) else None,
            source_url=data.get("source_url"),
            confidence=float(data.get("confidence") or 0.0),
            error_message=data.get("error_message"),
            candidates=[
                Authority.model_validate(candidate) for candidate in candidates if isinstance(candidate, dict)
            ],
            provider_metadata=data.get("provider_metadata") if isinstance(data.get("provider_metadata"), dict) else {},
        )
