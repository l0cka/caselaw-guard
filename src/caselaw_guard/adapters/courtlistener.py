from __future__ import annotations

import re
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
    ):
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)

    def lookup(self, citation: CitationMatch) -> LookupResult:
        data = self._citation_payload(citation)
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
            return LookupResult(
                status=VerificationStatus.RATE_LIMITED,
                normalized_citation=citation.text,
                error_message="CourtListener rate limit exceeded.",
            )
        if response.status_code >= 400:
            return LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message=f"CourtListener returned HTTP {response.status_code}.",
            )

        try:
            payload = response.json()
        except ValueError:
            return LookupResult(
                status=VerificationStatus.PROVIDER_ERROR,
                normalized_citation=citation.text,
                error_message="CourtListener returned non-JSON content.",
            )

        if not isinstance(payload, list) or not payload:
            return LookupResult(status=VerificationStatus.NOT_FOUND, normalized_citation=citation.text)

        return self._lookup_result_from_entry(payload[0], citation.text)

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
        authority = self._authority_from_cluster(clusters[0]) if clusters else None
        source_url = authority.source_url if authority else None

        return LookupResult(
            status=status,
            normalized_citation=normalized,
            authority=authority,
            source_url=source_url,
            confidence=self._confidence(status),
            error_message=entry.get("error_message") or None,
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
