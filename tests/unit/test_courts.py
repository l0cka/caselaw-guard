from openbench.courts import resolve_court


def test_known_federal_court_resolves() -> None:
    assert resolve_court("HCA") == ("High Court of Australia", "cth")


def test_known_state_court_resolves() -> None:
    assert resolve_court("NSWSC") == ("Supreme Court of New South Wales", "nsw")


def test_unknown_court_returns_nones() -> None:
    assert resolve_court("ZZZZ") == (None, None)


def test_resolve_court_is_case_sensitive_on_input() -> None:
    # callers are expected to upper-case before calling; mapping is upper-case only
    assert resolve_court("hca") == (None, None)
