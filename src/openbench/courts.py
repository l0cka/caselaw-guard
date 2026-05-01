"""Static mapping from Australian court codes to (name, jurisdiction)."""

from __future__ import annotations

# Jurisdiction codes follow Australian conventions: cth, nsw, vic, qld, wa, sa, tas, act, nt.
COURTS: dict[str, tuple[str, str]] = {
    # Commonwealth
    "HCA": ("High Court of Australia", "cth"),
    "FCAFC": ("Full Court of the Federal Court of Australia", "cth"),
    "FCA": ("Federal Court of Australia", "cth"),
    "FCCA": ("Federal Circuit Court of Australia", "cth"),
    "FedCFamC1A": ("Federal Circuit and Family Court of Australia (Division 1) Appellate", "cth"),
    "FedCFamC1F": ("Federal Circuit and Family Court of Australia (Division 1)", "cth"),
    "FedCFamC2F": ("Federal Circuit and Family Court of Australia (Division 2)", "cth"),
    "FamCA": ("Family Court of Australia", "cth"),
    "FamCAFC": ("Full Court of the Family Court of Australia", "cth"),
    "AATA": ("Administrative Appeals Tribunal", "cth"),
    # New South Wales
    "NSWCA": ("Court of Appeal of New South Wales", "nsw"),
    "NSWCCA": ("Court of Criminal Appeal of New South Wales", "nsw"),
    "NSWSC": ("Supreme Court of New South Wales", "nsw"),
    "NSWDC": ("District Court of New South Wales", "nsw"),
    "NSWLC": ("Local Court of New South Wales", "nsw"),
    # Victoria
    "VSCA": ("Court of Appeal of Victoria", "vic"),
    "VSC": ("Supreme Court of Victoria", "vic"),
    "VCC": ("County Court of Victoria", "vic"),
    # Queensland
    "QCA": ("Court of Appeal of Queensland", "qld"),
    "QSC": ("Supreme Court of Queensland", "qld"),
    "QDC": ("District Court of Queensland", "qld"),
    # Western Australia
    "WASCA": ("Court of Appeal of Western Australia", "wa"),
    "WASC": ("Supreme Court of Western Australia", "wa"),
    # South Australia
    "SASCFC": ("Full Court of the Supreme Court of South Australia", "sa"),
    "SASC": ("Supreme Court of South Australia", "sa"),
    # Tasmania
    "TASFC": ("Full Court of the Supreme Court of Tasmania", "tas"),
    "TASSC": ("Supreme Court of Tasmania", "tas"),
    # ACT
    "ACTCA": ("Court of Appeal of the Australian Capital Territory", "act"),
    "ACTSC": ("Supreme Court of the Australian Capital Territory", "act"),
    # Northern Territory
    "NTCA": ("Court of Appeal of the Northern Territory", "nt"),
    "NTSC": ("Supreme Court of the Northern Territory", "nt"),
}


def resolve_court(court_code: str) -> tuple[str | None, str | None]:
    """Return (court_name, jurisdiction) for a court code, or (None, None) if unknown.

    The mapping is upper-case only. Callers should normalise input to upper-case
    before calling (the citation parser does this).
    """
    info = COURTS.get(court_code)
    if info is None:
        return (None, None)
    return info
