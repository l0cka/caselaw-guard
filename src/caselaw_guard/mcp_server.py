from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Any

from caselaw_guard.adapters.base import CitationAdapter
from caselaw_guard.verifier import verify_text


def verify_case_law_text(
    text: str,
    *,
    adapters: Sequence[CitationAdapter] | None = None,
) -> dict[str, Any]:
    """Verify case-law citations in text and return the public report shape."""
    return _verification_report_payload(text=text, adapters=adapters)


def _verification_report_payload(
    *,
    text: str,
    adapters: Sequence[CitationAdapter] | None = None,
) -> dict[str, Any]:
    report = verify_text(text, adapters=adapters)
    return report.model_dump(by_alias=True)


def create_mcp_server(*, adapters: Sequence[CitationAdapter] | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as error:
        if error.name == "mcp":
            raise _missing_mcp_extra_error() from error
        raise

    mcp = FastMCP(
        "CaseLaw Guard",
        instructions=(
            "Verify case-law citation existence in supplied text. "
            "The tool fails closed when any citation is unresolved."
        ),
    )

    @mcp.tool()
    def verify_case_law_text(text: str) -> dict[str, Any]:
        """Verify case-law citations in plain text or Markdown."""
        return _verification_report_payload(text=text, adapters=adapters)

    return mcp


def main() -> None:
    try:
        mcp = create_mcp_server()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error

    mcp.run(transport="stdio")


def _missing_mcp_extra_error() -> RuntimeError:
    return RuntimeError(
        "MCP support is not installed. Install it with: python3 -m pip install 'caselaw-guard[mcp]'"
    )


if __name__ == "__main__":
    main()
