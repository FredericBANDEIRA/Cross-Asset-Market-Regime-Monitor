"""Tests for regime classification logic (from ui_design.py).

IMPORTANT: The thresholds below MUST stay in sync with ui_design.py.
If you change thresholds there, update them here too.
"""

# --- Thresholds (must match ui_design.py) ---
GROWTH_HIGH = 0.04
GROWTH_LOW = 0.02
INFLATION_HIGH = 0.03
INFLATION_LOW = 0.025


def classify_regime(row):
    """
    Mirror of the classify_regime function from ui_design.py.
    Copied here to test without launching Streamlit.
    """
    g = row.get("GDP", 0)
    i = row.get("CPIAUCNS", 0)

    if g > GROWTH_HIGH and i < INFLATION_LOW:
        return "Goldilocks"
    elif g > GROWTH_HIGH and i >= INFLATION_HIGH:
        return "Overheating"
    elif g <= GROWTH_LOW and i >= INFLATION_HIGH:
        return "Stagflation"
    elif g <= GROWTH_LOW and i < INFLATION_LOW:
        return "Deflation"
    elif g > GROWTH_LOW and i < INFLATION_LOW:
        return "Reflation"
    elif g > GROWTH_LOW and i >= INFLATION_LOW:
        return "Overheating"
    else:
        return "Deflation"


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
