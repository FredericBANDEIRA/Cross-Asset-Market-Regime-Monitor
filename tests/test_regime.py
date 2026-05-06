"""Tests for regime classification logic — imported from core.py.

No more copied functions or thresholds. Tests import directly from the
single source of truth.
"""

import pytest
from dashboard.core import classify_regime
from dashboard.config import (
    GROWTH_HIGH,
    GROWTH_LOW,
    INFLATION_HIGH,
    INFLATION_LOW,
)


# ----- Test each regime -----


def test_goldilocks():
    """High growth + low inflation → Goldilocks."""
    row = {"GDP": 0.05, "CPIAUCNS": 0.02}
    assert classify_regime(row) == "Goldilocks"


def test_overheating_high_growth():
    """High growth + high inflation → Overheating."""
    row = {"GDP": 0.05, "CPIAUCNS": 0.04}
    assert classify_regime(row) == "Overheating"


def test_overheating_moderate_growth():
    """Moderate growth + moderate inflation → Overheating."""
    row = {"GDP": 0.03, "CPIAUCNS": 0.026}
    assert classify_regime(row) == "Overheating"


def test_stagflation():
    """Low growth + high inflation → Stagflation."""
    row = {"GDP": 0.01, "CPIAUCNS": 0.04}
    assert classify_regime(row) == "Stagflation"


def test_reflation():
    """Moderate growth + low inflation → Reflation."""
    row = {"GDP": 0.03, "CPIAUCNS": 0.02}
    assert classify_regime(row) == "Reflation"


def test_deflation():
    """Low growth + low inflation → Deflation."""
    row = {"GDP": 0.01, "CPIAUCNS": 0.02}
    assert classify_regime(row) == "Deflation"


# ----- Edge cases -----


def test_boundary_goldilocks_growth():
    """GDP exactly at GROWTH_HIGH should NOT be Goldilocks (requires >)."""
    row = {"GDP": GROWTH_HIGH, "CPIAUCNS": 0.02}
    assert classify_regime(row) != "Goldilocks"


def test_boundary_stagflation_inflation():
    """CPI exactly at INFLATION_HIGH with low growth → Stagflation."""
    row = {"GDP": 0.01, "CPIAUCNS": INFLATION_HIGH}
    assert classify_regime(row) == "Stagflation"


def test_missing_keys_defaults_to_zero():
    """Missing GDP/CPI keys should default to 0 → Deflation."""
    row = {}
    assert classify_regime(row) == "Deflation"


def test_all_regimes_covered():
    """Ensure we have at least one test for each of the 5 regimes."""
    regimes = set()
    test_cases = [
        {"GDP": 0.05, "CPIAUCNS": 0.02},  # Goldilocks
        {"GDP": 0.03, "CPIAUCNS": 0.026},  # Overheating
        {"GDP": 0.01, "CPIAUCNS": 0.04},  # Stagflation
        {"GDP": 0.03, "CPIAUCNS": 0.02},  # Reflation
        {"GDP": 0.01, "CPIAUCNS": 0.02},  # Deflation
    ]
    for case in test_cases:
        regimes.add(classify_regime(case))

    expected = {"Goldilocks", "Overheating", "Stagflation", "Reflation", "Deflation"}
    assert regimes == expected


# ----- Ambiguous zone tests (previously buggy) -----


def test_moderate_growth_moderate_inflation():
    """GDP 2-4% + CPI 2.5-3% → Overheating (moderate growth, rising prices)."""
    row = {"GDP": 0.03, "CPIAUCNS": 0.028}
    assert classify_regime(row) == "Overheating"


def test_weak_growth_moderate_inflation():
    """GDP ≤ 2% + CPI 2.5-3% (below INFLATION_HIGH) → Deflation."""
    row = {"GDP": 0.015, "CPIAUCNS": 0.028}
    assert classify_regime(row) == "Deflation"


def test_weak_growth_at_inflation_boundary():
    """GDP ≤ 2% + CPI exactly at INFLATION_HIGH → Stagflation."""
    row = {"GDP": 0.015, "CPIAUCNS": INFLATION_HIGH}
    assert classify_regime(row) == "Stagflation"


def test_high_growth_at_inflation_boundary():
    """GDP > 4% + CPI exactly at INFLATION_LOW → Overheating."""
    row = {"GDP": 0.05, "CPIAUCNS": INFLATION_LOW}
    assert classify_regime(row) == "Overheating"


def test_growth_at_low_boundary_low_inflation():
    """GDP exactly at GROWTH_LOW + low CPI → Deflation (≤ boundary)."""
    row = {"GDP": GROWTH_LOW, "CPIAUCNS": 0.01}
    assert classify_regime(row) == "Deflation"


def test_growth_just_above_low_boundary():
    """GDP just above GROWTH_LOW + low CPI → Reflation."""
    row = {"GDP": GROWTH_LOW + 0.001, "CPIAUCNS": 0.01}
    assert classify_regime(row) == "Reflation"


# ----- Parametrized sweep -----


@pytest.mark.parametrize(
    "gdp, cpi, expected",
    [
        # Strong growth zone
        (0.06, 0.01, "Goldilocks"),
        (0.06, 0.024, "Goldilocks"),
        (0.06, 0.025, "Overheating"),
        (0.06, 0.04, "Overheating"),
        # Moderate growth zone
        (0.03, 0.01, "Reflation"),
        (0.03, 0.024, "Reflation"),
        (0.03, 0.025, "Overheating"),
        (0.03, 0.04, "Overheating"),
        # Weak growth zone
        (0.01, 0.01, "Deflation"),
        (0.01, 0.029, "Deflation"),
        (0.01, 0.03, "Stagflation"),
        (0.01, 0.05, "Stagflation"),
        # Negative values
        (-0.01, -0.01, "Deflation"),
        (-0.01, 0.05, "Stagflation"),
    ],
)
def test_regime_parametrized(gdp, cpi, expected):
    """Sweep GDP/CPI combinations to ensure full decision-tree coverage."""
    row = {"GDP": gdp, "CPIAUCNS": cpi}
    assert classify_regime(row) == expected
