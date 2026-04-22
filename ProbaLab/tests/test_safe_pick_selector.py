"""Tests unitaires pour la logique pure `select_safe_pick` (Lot 2 · T02).

Contrat du selector :
- Priorité aux pics simples dans la bande [1.80, 2.20] + confidence >= MIN_CONFIDENCE_SINGLE.
- Si aucun single ne passe, tenter un combo 2 legs dont le produit ∈ [1.80, 2.20].
- Sinon `safe_pick=None` + `fallback_message`.
"""

from __future__ import annotations

from src.models.safe_pick_selector import select_safe_pick


def test_single_bet_in_band_wins_over_combo() -> None:
    """Quand un single est dans la bande avec confidence suffisante, on le préfère."""
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 2.00, "confidence": 0.72},
        {"fixture_id": "f2", "market": "OU", "selection": "O2.5", "odds": 1.85, "confidence": 0.65},
        # 3.10 hors bande haute
        {"fixture_id": "f3", "market": "1X2", "selection": "A", "odds": 3.10, "confidence": 0.80},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["fixture_id"] == "f1"  # plus haute confidence dans la bande


def test_single_nhl_in_band_selected() -> None:
    """Un pick NHL dans la bande est retenu au même titre qu'un football."""
    candidates = [
        {
            "fixture_id": "nhl_77",
            "sport": "nhl",
            "market": "WIN",
            "selection": "home",
            "odds": 1.95,
            "confidence": 0.68,
        },
        # Foot hors bande haute
        {
            "fixture_id": "f1",
            "sport": "football",
            "market": "1X2",
            "selection": "A",
            "odds": 3.50,
            "confidence": 0.80,
        },
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["fixture_id"] == "nhl_77"


def test_fallback_combo_2_legs() -> None:
    """Pas de single dans la bande → combo 2 legs dont le produit ∈ [1.80, 2.20]."""
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 1.40, "confidence": 0.82},
        {"fixture_id": "f2", "market": "OU", "selection": "O2.5", "odds": 1.45, "confidence": 0.78},
        # produit 1.40 * 1.45 = 2.03 ∈ [1.80, 2.20]
        {"fixture_id": "f3", "market": "1X2", "selection": "X", "odds": 3.20, "confidence": 0.50},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "combo"
    assert len(out["safe_pick"]["legs"]) == 2
    product = out["safe_pick"]["legs"][0]["odds"] * out["safe_pick"]["legs"][1]["odds"]
    assert 1.80 <= product <= 2.20


def test_no_pick_returns_fallback_message() -> None:
    """Rien d'éligible (singles hors bande + pas de combo possible) → safe_pick None + message."""
    candidates = [
        # Trop haut (hors bande haute pour single)
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 3.50, "confidence": 0.70},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is None
    assert "fallback_message" in out
    assert out["fallback_message"]


def test_single_at_exact_upper_bound_is_eligible() -> None:
    """La borne haute 2.20 doit rester éligible (inclusive) pour éviter les bugs d'arrondi."""
    candidates = [
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 2.20, "confidence": 0.61},
    ]
    out = select_safe_pick(candidates)
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "single"
    assert out["safe_pick"]["odds"] == 2.20


def test_single_below_min_confidence_is_ignored() -> None:
    """Une cote dans la bande mais confidence < MIN_CONFIDENCE_SINGLE → pas retenu."""
    candidates = [
        # Dans la bande mais confidence trop basse
        {"fixture_id": "f1", "market": "1X2", "selection": "H", "odds": 2.00, "confidence": 0.40},
        # Combo possible 1.50 * 1.45 = 2.175 ∈ bande
        {"fixture_id": "f2", "market": "OU", "selection": "O2.5", "odds": 1.50, "confidence": 0.70},
        {"fixture_id": "f3", "market": "1X2", "selection": "X", "odds": 1.45, "confidence": 0.70},
    ]
    out = select_safe_pick(candidates)
    # Le single à 2.00 n'est pas retenu (confidence trop faible).
    # Fallback combo : produit(1.50 * 1.45) = 2.175 ∈ [1.80, 2.20]
    assert out["safe_pick"] is not None
    assert out["safe_pick"]["type"] == "combo"
