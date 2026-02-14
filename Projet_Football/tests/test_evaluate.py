"""
Tests unitaires pour evaluate.py — fonctions pures d'évaluation.
"""

from training.evaluate import _check_recommended_bet

# ═══════════════════════════════════════════════════════════════════
#  VÉRIFICATION DU PARI RECOMMANDÉ
# ═══════════════════════════════════════════════════════════════════


class TestCheckRecommendedBet:
    """Tests de la vérification si le pari recommandé était gagnant."""

    def test_victoire_domicile_correct(self):
        assert _check_recommended_bet("Victoire Domicile", "H", False, False, 1) is True

    def test_victoire_domicile_incorrect(self):
        assert _check_recommended_bet("Victoire Domicile", "A", False, False, 2) is False

    def test_victoire_exterieur_correct(self):
        assert _check_recommended_bet("Victoire Extérieur", "A", False, True, 3) is True

    def test_nul_correct(self):
        assert _check_recommended_bet("Match Nul", "D", True, False, 2) is True

    def test_btts_correct(self):
        assert _check_recommended_bet("BTTS Oui", "H", True, True, 3) is True

    def test_btts_incorrect(self):
        assert _check_recommended_bet("BTTS Oui", "H", False, False, 1) is False

    def test_over_25_correct(self):
        assert _check_recommended_bet("Plus de 2.5 buts", "H", True, True, 4) is True

    def test_over_25_incorrect(self):
        assert _check_recommended_bet("Plus de 2.5 buts", "D", False, False, 1) is False

    def test_empty_bet_returns_false(self):
        assert _check_recommended_bet("", "H", True, True, 3) is False

    def test_none_bet_returns_false(self):
        assert _check_recommended_bet(None, "H", True, True, 3) is False
