"""Australian neutral-citation court metadata."""

from __future__ import annotations

# This is the union of the previous CaseLaw Guard extraction allowlist and the
# OpenBench metadata table.  Values preserve the conventional spelling used by
# each court code; lookup remains case-insensitive.
COURTS: dict[str, tuple[str, str]] = {
    "HCA": ("High Court of Australia", "cth"),
    "FCAFC": ("Full Court of the Federal Court of Australia", "cth"),
    "FCA": ("Federal Court of Australia", "cth"),
    "FCCA": ("Federal Circuit Court of Australia", "cth"),
    "FCFCOA": ("Federal Circuit and Family Court of Australia", "cth"),
    "FedCFamC1A": ("Federal Circuit and Family Court of Australia (Division 1) Appellate", "cth"),
    "FedCFamC1F": ("Federal Circuit and Family Court of Australia (Division 1)", "cth"),
    "FedCFamC2F": ("Federal Circuit and Family Court of Australia (Division 2)", "cth"),
    "FamCA": ("Family Court of Australia", "cth"),
    "FamCAFC": ("Full Court of the Family Court of Australia", "cth"),
    "AATA": ("Administrative Appeals Tribunal", "cth"),
    "ART": ("Administrative Review Tribunal", "cth"),
    "FWC": ("Fair Work Commission", "cth"),
    "NSWCA": ("Court of Appeal of New South Wales", "nsw"),
    "NSWCCA": ("Court of Criminal Appeal of New South Wales", "nsw"),
    "NSWSC": ("Supreme Court of New South Wales", "nsw"),
    "NSWDC": ("District Court of New South Wales", "nsw"),
    "NSWLC": ("Local Court of New South Wales", "nsw"),
    "NSWCAT": ("New South Wales Civil and Administrative Tribunal", "nsw"),
    "NSWCATAP": ("New South Wales Civil and Administrative Tribunal Appeal Panel", "nsw"),
    "NSWCATAD": ("New South Wales Civil and Administrative Tribunal Appeal Division", "nsw"),
    "NSWCATOD": ("New South Wales Civil and Administrative Tribunal Occupational Division", "nsw"),
    "NSWCATEN": ("New South Wales Civil and Administrative Tribunal Enforcement", "nsw"),
    "NSWLEC": ("Land and Environment Court of New South Wales", "nsw"),
    "NSWADT": ("Administrative Decisions Tribunal of New South Wales", "nsw"),
    "NSWADTAP": ("Administrative Decisions Tribunal Appeal Panel of New South Wales", "nsw"),
    "NSWIRComm": ("Industrial Relations Commission of New South Wales", "nsw"),
    "NSWMT": ("New South Wales Mining Tribunal", "nsw"),
    "VCA": ("Court of Appeal of Victoria", "vic"),
    "VSCA": ("Court of Appeal of Victoria", "vic"),
    "VSC": ("Supreme Court of Victoria", "vic"),
    "VCC": ("County Court of Victoria", "vic"),
    "QCA": ("Court of Appeal of Queensland", "qld"),
    "QSC": ("Supreme Court of Queensland", "qld"),
    "QDC": ("District Court of Queensland", "qld"),
    "WASCA": ("Court of Appeal of Western Australia", "wa"),
    "WASC": ("Supreme Court of Western Australia", "wa"),
    "SASCFC": ("Full Court of the Supreme Court of South Australia", "sa"),
    "SASCA": ("Court of Appeal of South Australia", "sa"),
    "SASC": ("Supreme Court of South Australia", "sa"),
    "TASFC": ("Full Court of the Supreme Court of Tasmania", "tas"),
    "TASSC": ("Supreme Court of Tasmania", "tas"),
    "ACTCA": ("Court of Appeal of the Australian Capital Territory", "act"),
    "ACTSC": ("Supreme Court of the Australian Capital Territory", "act"),
    "NTCA": ("Court of Appeal of the Northern Territory", "nt"),
    "NTSC": ("Supreme Court of the Northern Territory", "nt"),
}

_COURTS_BY_FOLDED_CODE = {code.casefold(): (code, *details) for code, details in COURTS.items()}


def canonical_court_code(court_code: str) -> str:
    """Return a known code's conventional spelling, else uppercase it."""
    known = _COURTS_BY_FOLDED_CODE.get(court_code.casefold())
    return known[0] if known else court_code.upper()


def resolve_court(court_code: str) -> tuple[str | None, str | None]:
    """Return court metadata for a code, accepting any input casing."""
    known = _COURTS_BY_FOLDED_CODE.get(court_code.casefold())
    return (known[1], known[2]) if known else (None, None)
