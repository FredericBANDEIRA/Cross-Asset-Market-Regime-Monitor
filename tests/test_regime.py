"""Tests for regime classification logic (from ui_design.py)."""

import pandas as pd
import pytest


def classify_regime(row):
    """
    Mirror of the classify_regime function from ui_design.py.
    Copied here to test without launching Streamlit.
    """
    g = row.get("GDP", 0)
    i = row.get("CPIAUCNS", 0)

    if g > 0.02 and i < 0.02:
        return "Goldilocks"
    elif g > 0.02 and i >= 0.025:
        return "Overheating"
    elif g <= 0.01 and i >= 0.025:
        return "Stagflation"
    elif g > 0.01 and i < 0.015:
        return "Reflation"
    else:
        return "Deflation"


# ----- Test each regime -----


def test_goldilocks():
    """High growth + low inflation → Goldilocks."""
    row = {"GDP": 0.03, "CPIAUCNS": 0.01}
    assert classify_regime(row) == "Goldilocks"


def test_overheating():
    """High growth + high inflation → Overheating."""
    row = {"GDP": 0.03, "CPIAUCNS": 0.03}
    assert classify_regime(row) == "Overheating"


def test_stagflation():
    """Low growth + high inflation → Stagflation."""
    row = {"GDP": 0.005, "CPIAUCNS": 0.03}
    assert classify_regime(row) == "Stagflation"


def test_reflation():
    """Moderate growth + very low inflation → Reflation."""
    row = {"GDP": 0.015, "CPIAUCNS": 0.01}
    assert classify_regime(row) == "Reflation"


def test_deflation():
    """Moderate growth + moderate inflation (no regime matches) → Deflation."""
    row = {"GDP": 0.015, "CPIAUCNS": 0.02}
    assert classify_regime(row) == "Deflation"


# ----- Edge cases -----


def test_boundary_goldilocks_growth():
    """GDP exactly at 0.02 should NOT be Goldilocks (requires >0.02)."""
    row = {"GDP": 0.02, "CPIAUCNS": 0.01}
    assert classify_regime(row) != "Goldilocks"


def test_boundary_stagflation_inflation():
    """CPI exactly at 0.025 with low growth → Stagflation."""
    row = {"GDP": 0.005, "CPIAUCNS": 0.025}
    assert classify_regime(row) == "Stagflation"


def test_missing_keys_defaults_to_zero():
    """Missing GDP/CPI keys should default to 0 → Deflation."""
    row = {}
    assert classify_regime(row) == "Deflation"


def test_all_regimes_covered():
    """Ensure we have at least one test for each of the 5 regimes."""
    regimes = set()
    test_cases = [
        {"GDP": 0.03, "CPIAUCNS": 0.01},  # Goldilocks
        {"GDP": 0.03, "CPIAUCNS": 0.03},  # Overheating
        {"GDP": 0.005, "CPIAUCNS": 0.03},  # Stagflation
        {"GDP": 0.015, "CPIAUCNS": 0.01},  # Reflation
        {"GDP": 0.015, "CPIAUCNS": 0.02},  # Deflation
    ]
    for case in test_cases:
        regimes.add(classify_regime(case))

    expected = {"Goldilocks", "Overheating", "Stagflation", "Reflation", "Deflation"}
    assert regimes == expected
