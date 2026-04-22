"""tests/test_odds_comparator.py — Unit tests for ``build_comparison`` (Lot 2 · T04).

Verifies the pure function groups odds rows by market/selection and flags the
single best odds per selection across bookmakers.
"""

from __future__ import annotations

from src.models.odds_comparator import build_comparison


def test_best_odds_flagged_per_selection():
    """Within one market/selection, the highest odds wins the ``is_best`` flag."""
    rows = [
        {"market": "1X2", "selection": "H", "bookmaker": "Winamax", "odds": 1.85},
        {"market": "1X2", "selection": "H", "bookmaker": "Unibet", "odds": 1.92},
        {"market": "1X2", "selection": "X", "bookmaker": "Winamax", "odds": 3.40},
    ]

    out = build_comparison(rows)

    assert out["1X2"]["H"][0]["bookmaker"] == "Unibet"
    assert out["1X2"]["H"][0]["is_best"] is True
    assert out["1X2"]["H"][1]["is_best"] is False
    assert out["1X2"]["X"][0]["is_best"] is True


def test_multi_market_grouping():
    """Rows are grouped by market then by selection; each selection sorted DESC."""
    rows = [
        {"market": "BTTS", "selection": "Yes", "bookmaker": "PMU", "odds": 1.70},
        {"market": "BTTS", "selection": "Yes", "bookmaker": "Betclic", "odds": 1.80},
        {"market": "BTTS", "selection": "No", "bookmaker": "PMU", "odds": 2.10},
        {"market": "1X2", "selection": "H", "bookmaker": "PMU", "odds": 2.00},
    ]

    out = build_comparison(rows)

    assert set(out.keys()) == {"BTTS", "1X2"}
    assert out["BTTS"]["Yes"][0]["bookmaker"] == "Betclic"
    assert out["BTTS"]["Yes"][0]["odds"] == 1.80
    assert out["BTTS"]["No"][0]["bookmaker"] == "PMU"
    assert out["1X2"]["H"][0]["odds"] == 2.00


def test_empty_rows_returns_empty_dict():
    """No rows → empty comparison mapping (no crash)."""
    assert build_comparison([]) == {}


def test_odds_coerced_to_float():
    """String/Decimal odds inputs are coerced to float so the output stays typed."""
    rows = [
        {"market": "1X2", "selection": "H", "bookmaker": "X", "odds": "1.85"},
        {"market": "1X2", "selection": "H", "bookmaker": "Y", "odds": 2},
    ]

    out = build_comparison(rows)

    assert out["1X2"]["H"][0]["bookmaker"] == "Y"
    assert isinstance(out["1X2"]["H"][0]["odds"], float)
    assert out["1X2"]["H"][0]["odds"] == 2.0


def test_single_bookmaker_is_best():
    """A sole bookmaker per selection is still flagged as best."""
    rows = [{"market": "1X2", "selection": "A", "bookmaker": "PMU", "odds": 4.50}]

    out = build_comparison(rows)

    assert out["1X2"]["A"][0]["is_best"] is True
    assert len(out["1X2"]["A"]) == 1
