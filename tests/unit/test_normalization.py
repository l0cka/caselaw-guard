from datetime import datetime

import pytest

from openbench.normalization import (
    extract_case_name_and_citation,
    normalize_citation,
)

# Accepted forms — must all normalise to "[1992] HCA 23"
ACCEPTED = [
    "[1992] HCA 23",
    "(1992) HCA 23",
    "1992 HCA 23",
    "[1992]  HCA   23",
    "  [1992] HCA 23  ",
    "[1992] hca 23",
    "[1992] HCA 23 [10]",
    "[1992] HCA 23 at [10]",
    "[1992] HCA 23, [10]",
]


@pytest.mark.parametrize("raw", ACCEPTED)
def test_canonical_and_variants_normalise(raw: str) -> None:
    result = normalize_citation(raw)
    assert result.ok is True
    assert result.normalized == "[1992] HCA 23"
    assert result.year == 1992
    assert result.court_code == "HCA"
    assert result.number == 23


REJECTED = [
    "",
    "Mabo",
    "(1992) 175 CLR 1",  # reported citation rejected in v1
    "[abcd] HCA 23",
    "[1992] HCA",
    "[1992] HCA abc",
    "[1899] HCA 1",  # below year floor
    "[3000] HCA 1",  # above year ceiling
    "[1992] 23",     # missing court
    "HCA 23",        # missing year
]


@pytest.mark.parametrize("raw", REJECTED)
def test_invalid_inputs_rejected(raw: str) -> None:
    result = normalize_citation(raw)
    assert result.ok is False
    assert result.normalized is None


def test_extract_case_name_strips_neutral_citation() -> None:
    raw = "Mabo v Queensland (No 2) [1992] HCA 23"
    case_name, normalized = extract_case_name_and_citation(raw)
    assert case_name == "Mabo v Queensland (No 2)"
    assert normalized == "[1992] HCA 23"


def test_extract_case_name_handles_paren_year_form() -> None:
    case_name, normalized = extract_case_name_and_citation("Foo v Bar (1992) HCA 23")
    assert case_name == "Foo v Bar"
    assert normalized == "[1992] HCA 23"


def test_extract_case_name_returns_none_when_no_citation() -> None:
    case_name, normalized = extract_case_name_and_citation("Mabo")
    assert case_name is None
    assert normalized is None


def test_year_ceiling_uses_current_year_plus_one() -> None:
    next_year = datetime.now().year + 1
    res = normalize_citation(f"[{next_year}] HCA 1")
    assert res.ok is True
    too_far = normalize_citation(f"[{next_year + 1}] HCA 1")
    assert too_far.ok is False


def test_normalization_result_is_immutable_dataclass() -> None:
    res = normalize_citation("[1992] HCA 23")
    with pytest.raises((AttributeError, TypeError)):
        res.normalized = "[2000] HCA 1"  # type: ignore[misc]
