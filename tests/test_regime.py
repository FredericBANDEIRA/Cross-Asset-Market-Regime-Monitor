"""Tests for regime classification logic — imported from core.py.

No more copied functions or thresholds. Tests import directly from the
single source of truth.
"""

from dashboard.core import classify_regime
from dashboard.config import (
    GROWTH_HIGH,
    INFLATION_HIGH,
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
