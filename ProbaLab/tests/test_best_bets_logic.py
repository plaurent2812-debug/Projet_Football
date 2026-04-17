"""
tests/test_best_bets_logic.py — Unit tests for pure best bets logic.

These tests cover the business rules extracted from best_bets.py into
api.routers.best_bets_logic. No Supabase, no FastAPI, no side effects —
just plain functions operating on dicts and primitives.
"""

from __future__ import annotations

import pytest

from api.routers.best_bets_logic import (
    MARKET_NORMALIZE,
    build_market_breakdown,
    calc_stats,
    evaluate_football_combo,
    evaluate_nhl_player_market,
    evaluate_single_football_market,
    extract_nhl_market_from_label,
    normalize_market,
)

# ═══════════════════════════════════════════════════════════════════
#  evaluate_single_football_market
# ═══════════════════════════════════════════════════════════════════


class TestEvaluateSingleFootballMarket:
    """Cover every market branch and both WIN/LOSS outcomes."""

    # ── 1X2 markets ──────────────────────────────────────────────
    def test_victoire_domicile_win(self):
        assert evaluate_single_football_market("Victoire domicile", 2, 1) == "WIN"

    def test_victoire_domicile_loss_draw(self):
        # Draw is not a home win
        assert evaluate_single_football_market("Victoire domicile", 1, 1) == "LOSS"

    def test_victoire_domicile_loss_away(self):
        assert evaluate_single_football_market("Victoire domicile", 0, 2) == "LOSS"

    def test_victoire_exterieur_win(self):
        assert evaluate_single_football_market("Victoire extérieur", 0, 3) == "WIN"

    def test_victoire_exterieur_loss(self):
        assert evaluate_single_football_market("Victoire extérieur", 2, 1) == "LOSS"

    def test_match_nul_win(self):
        assert evaluate_single_football_market("Match nul", 1, 1) == "WIN"

    def test_match_nul_loss(self):
        assert evaluate_single_football_market("Match nul", 2, 1) == "LOSS"

    # ── Double Chance ────────────────────────────────────────────
    def test_double_chance_1n_win_home(self):
        assert evaluate_single_football_market("Double Chance 1N", 2, 0) == "WIN"

    def test_double_chance_1n_win_draw(self):
        assert evaluate_single_football_market("Double Chance 1N", 1, 1) == "WIN"

    def test_double_chance_1n_loss_away_win(self):
        assert evaluate_single_football_market("Double Chance 1N", 0, 2) == "LOSS"

    def test_double_chance_1x_win_draw(self):
        # Double Chance 1X and 1N share the same semantics (home or draw)
        assert evaluate_single_football_market("Double Chance 1X", 0, 0) == "WIN"

    def test_double_chance_x2_win_away(self):
        assert evaluate_single_football_market("Double Chance X2", 0, 2) == "WIN"

    def test_double_chance_x2_win_draw(self):
        assert evaluate_single_football_market("Double Chance X2", 2, 2) == "WIN"

    def test_double_chance_x2_loss_home_win(self):
        assert evaluate_single_football_market("Double Chance X2", 3, 1) == "LOSS"

    # ── Over buts ────────────────────────────────────────────────
    def test_over_25_win_on_3(self):
        assert evaluate_single_football_market("Over 2.5 buts", 2, 1) == "WIN"

    def test_over_25_loss_on_2(self):
        assert evaluate_single_football_market("Over 2.5 buts", 1, 1) == "LOSS"

    def test_over_15_win_on_2(self):
        assert evaluate_single_football_market("Over 1.5 buts", 1, 1) == "WIN"

    def test_over_15_loss_on_1(self):
        assert evaluate_single_football_market("Over 1.5 buts", 1, 0) == "LOSS"

    def test_over_35_win_on_4(self):
        assert evaluate_single_football_market("Over 3.5 buts", 3, 1) == "WIN"

    def test_over_35_loss_on_3(self):
        assert evaluate_single_football_market("Over 3.5 buts", 2, 1) == "LOSS"

    # ── BTTS aliases ─────────────────────────────────────────────
    @pytest.mark.parametrize(
        "market",
        [
            "BTTS",
            "BTTS Oui",
            "BTTS — Les deux équipes marquent",
        ],
    )
    def test_btts_win_both_scored(self, market):
        assert evaluate_single_football_market(market, 2, 1) == "WIN"

    @pytest.mark.parametrize(
        "market",
        [
            "BTTS",
            "BTTS Oui",
            "BTTS — Les deux équipes marquent",
        ],
    )
    def test_btts_loss_home_clean_sheet(self, market):
        assert evaluate_single_football_market(market, 2, 0) == "LOSS"

    def test_btts_loss_away_clean_sheet(self):
        assert evaluate_single_football_market("BTTS", 0, 3) == "LOSS"

    def test_btts_loss_zero_zero(self):
        assert evaluate_single_football_market("BTTS", 0, 0) == "LOSS"

    # ── Unknown markets ──────────────────────────────────────────
    def test_unknown_market_returns_none(self):
        assert evaluate_single_football_market("Corner Asian Handicap", 2, 1) is None

    def test_empty_market_returns_none(self):
        assert evaluate_single_football_market("", 2, 1) is None


# ═══════════════════════════════════════════════════════════════════
#  evaluate_football_combo
# ═══════════════════════════════════════════════════════════════════


class TestEvaluateFootballCombo:
    """Cover combo resolution rules."""

    def test_two_legs_all_win(self):
        # Home win + Over 2.5 on a 3-0
        assert evaluate_football_combo("Victoire domicile + Over 2.5 buts", 3, 0) == "WIN"

    def test_two_legs_one_loss_short_circuits(self):
        # Home win (WIN) + BTTS (LOSS, since away didn't score)
        assert evaluate_football_combo("Victoire domicile + BTTS Oui", 3, 0) == "LOSS"

    def test_three_legs_all_win(self):
        # 1-1 draw: Match nul WIN, Over 1.5 WIN, BTTS WIN
        assert evaluate_football_combo("Match nul + Over 1.5 buts + BTTS Oui", 1, 1) == "WIN"

    def test_three_legs_middle_loss(self):
        # 2-0 home win: V.dom WIN, Over 2.5 LOSS → combo LOSS
        assert (
            evaluate_football_combo("Victoire domicile + Over 2.5 buts + Match nul", 2, 0) == "LOSS"
        )

    def test_unknown_leg_returns_none(self):
        # Unknown market in the combo → stays PENDING (None)
        assert evaluate_football_combo("Victoire domicile + Corner Handicap", 2, 0) is None

    def test_unknown_leg_with_loss_still_loss(self):
        # A LOSS leg short-circuits before the unknown leg is even checked
        assert evaluate_football_combo("Victoire extérieur + Corner Handicap", 2, 0) == "LOSS"

    def test_combo_with_extra_whitespace(self):
        assert evaluate_football_combo("Victoire domicile  +  Over 1.5 buts", 2, 0) == "WIN"

    def test_single_leg_combo_behaves_as_single(self):
        # A "combo" with a single leg should resolve like the single market
        assert evaluate_football_combo("Victoire domicile", 2, 1) == "WIN"


# ═══════════════════════════════════════════════════════════════════
#  evaluate_nhl_player_market
# ═══════════════════════════════════════════════════════════════════


class TestEvaluateNHLPlayerMarket:
    """Cover every NHL player prop market."""

    def test_points_over_05_win(self):
        assert (
            evaluate_nhl_player_market(
                "player_points_over_0.5", points=1, goals=0, assists=1, shots=3
            )
            == "WIN"
        )

    def test_points_over_05_loss_on_zero(self):
        assert (
            evaluate_nhl_player_market(
                "player_points_over_0.5", points=0, goals=0, assists=0, shots=5
            )
            == "LOSS"
        )

    def test_goals_over_05_win(self):
        assert (
            evaluate_nhl_player_market(
                "player_goals_over_0.5", points=2, goals=1, assists=1, shots=4
            )
            == "WIN"
        )

    def test_goals_over_05_loss_on_assists_only(self):
        # Points > 0 but 0 goals should still be LOSS for the goals market
        assert (
            evaluate_nhl_player_market(
                "player_goals_over_0.5", points=2, goals=0, assists=2, shots=3
            )
            == "LOSS"
        )

    def test_assists_over_05_win(self):
        assert (
            evaluate_nhl_player_market(
                "player_assists_over_0.5", points=1, goals=0, assists=1, shots=2
            )
            == "WIN"
        )

    def test_assists_over_05_loss_on_goals_only(self):
        assert (
            evaluate_nhl_player_market(
                "player_assists_over_0.5", points=1, goals=1, assists=0, shots=3
            )
            == "LOSS"
        )

    def test_shots_over_25_win_at_3(self):
        # Threshold is 3 (over 2.5)
        assert (
            evaluate_nhl_player_market(
                "player_shots_over_2.5", points=0, goals=0, assists=0, shots=3
            )
            == "WIN"
        )

    def test_shots_over_25_loss_at_2(self):
        assert (
            evaluate_nhl_player_market(
                "player_shots_over_2.5", points=2, goals=1, assists=1, shots=2
            )
            == "LOSS"
        )

    def test_unknown_market_falls_back_to_points(self):
        # Fallback behavior must match the inline logic
        assert (
            evaluate_nhl_player_market(
                "player_mystery_market", points=1, goals=0, assists=1, shots=0
            )
            == "WIN"
        )
        assert (
            evaluate_nhl_player_market(
                "player_mystery_market", points=0, goals=0, assists=0, shots=0
            )
            == "LOSS"
        )


# ═══════════════════════════════════════════════════════════════════
#  extract_nhl_market_from_label
# ═══════════════════════════════════════════════════════════════════


class TestExtractNHLMarketFromLabel:
    def test_marquer_un_but(self):
        assert (
            extract_nhl_market_from_label("Leon Draisaitl — Marquer un but")
            == "player_goals_over_0.5"
        )

    def test_faire_une_passe(self):
        assert (
            extract_nhl_market_from_label("Connor McDavid — Faire une passe")
            == "player_assists_over_0.5"
        )

    def test_over_05_points(self):
        assert (
            extract_nhl_market_from_label("Nathan MacKinnon Over 0.5 Points — COL vs VGK")
            == "player_points_over_0.5"
        )

    def test_tirs_capital(self):
        assert extract_nhl_market_from_label("Auston Matthews — 3+ Tirs") == "player_shots_over_2.5"

    def test_tirs_lowercase(self):
        assert extract_nhl_market_from_label("david pastrnak tirs") == "player_shots_over_2.5"

    def test_unknown_label_defaults_to_points(self):
        assert extract_nhl_market_from_label("Unrecognized market") == "player_points_over_0.5"


# ═══════════════════════════════════════════════════════════════════
#  normalize_market
# ═══════════════════════════════════════════════════════════════════


class TestNormalizeMarket:
    def test_canonical_market_passthrough(self):
        assert normalize_market("Victoire domicile") == "Victoire domicile"

    def test_btts_alias(self):
        assert normalize_market("BTTS Oui") == "BTTS"

    def test_btts_long_alias(self):
        assert normalize_market("BTTS — Les deux équipes marquent") == "BTTS"

    def test_double_chance_variants_collapse(self):
        assert normalize_market("Double Chance 1X") == "Double Chance 1N"
        assert normalize_market("Double chance 1N") == "Double Chance 1N"

    def test_nhl_player_markets_to_french(self):
        assert normalize_market("player_points_over_0.5") == "Points (NHL)"
        assert normalize_market("player_goals_over_0.5") == "Buts (NHL)"
        assert normalize_market("player_assists_over_0.5") == "Passes (NHL)"
        assert normalize_market("player_shots_over_2.5") == "Tirs (NHL)"

    def test_expert_enrichment_duplicates_collapse(self):
        assert normalize_market("Points du joueur : 1 ou plus") == "Points (NHL)"
        assert normalize_market("Passes décisives du joueur : 1 ou plus") == "Passes (NHL)"
        assert normalize_market("Buts du joueur : 1 ou plus") == "Buts (NHL)"

    def test_category_with_label_extracts_actual_market(self):
        assert (
            normalize_market("safe_football", bet_label="PSG vs Lyon — Victoire domicile")
            == "Victoire domicile"
        )

    def test_category_with_label_applies_normalization(self):
        assert (
            normalize_market("fun_nhl", bet_label="McDavid — player_points_over_0.5")
            == "Points (NHL)"
        )

    def test_category_without_label_passes_through_as_raw(self):
        # Edge case: when bet_label is empty, the CATEGORY branch is skipped
        # (short-circuited by the `and bet_label` check) and the raw value
        # falls through to MARKET_NORMALIZE.get(raw, raw), returning the raw
        # category string. In practice, rows always carry a label in production,
        # so this path is a silent edge case we simply document here.
        assert normalize_market("safe_nhl") == "safe_nhl"

    def test_category_with_matchlike_extracted_value_is_skipped(self):
        # Label format "Team vs Team — …" where the part after — also contains "vs"
        assert (
            normalize_market("fun_football", bet_label="PSG vs Lyon — Marseille vs Lille")
            == "__skip__"
        )

    def test_raw_market_looking_like_match_name_is_skipped(self):
        assert normalize_market("Chelsea vs Arsenal") == "__skip__"

    def test_raw_market_looking_like_match_name_with_vs_dot(self):
        assert normalize_market("Bayern vs. Dortmund") == "__skip__"

    def test_every_entry_in_market_normalize_is_accessible(self):
        # Sanity: the MARKET_NORMALIZE dict contents should be reachable
        for raw, expected in MARKET_NORMALIZE.items():
            assert normalize_market(raw) == expected


# ═══════════════════════════════════════════════════════════════════
#  calc_stats
# ═══════════════════════════════════════════════════════════════════


def _make_bet(
    *,
    market: str = "Victoire domicile",
    result: str = "WIN",
    odds: float | None = 2.0,
    date: str = "2026-04-01",
) -> dict:
    """Build a minimal bet dict for calc_stats tests."""
    return {"market": market, "result": result, "odds": odds, "date": date}


class TestCalcStatsBasic:
    def test_empty_returns_zero_stats(self):
        s = calc_stats([])
        assert s["wins"] == 0
        assert s["losses"] == 0
        assert s["total"] == 0
        assert s["win_rate"] == 0
        assert s["roi_pct"] == 0
        assert s["roi_singles_pct"] == 0
        assert s["singles_count"] == 0
        assert s["combines_count"] == 0

    def test_single_win(self):
        s = calc_stats([_make_bet(result="WIN", odds=2.0)])
        assert s["wins"] == 1
        assert s["losses"] == 0
        assert s["total"] == 1
        assert s["win_rate"] == 100.0
        # ROI on 1 bet with odds 2.0, WIN → gain = 2.0 - 1 = 1.0; roi_pct = 100
        assert s["roi_pct"] == 100.0
        assert s["singles_count"] == 1
        assert s["roi_singles_pct"] == 100.0

    def test_single_loss(self):
        s = calc_stats([_make_bet(result="LOSS", odds=2.0)])
        assert s["wins"] == 0
        assert s["losses"] == 1
        assert s["win_rate"] == 0
        # ROI: -1 on 1 bet → -100%
        assert s["roi_pct"] == -100.0

    def test_mixed_wins_and_losses(self):
        bets = [
            _make_bet(result="WIN", odds=2.0),
            _make_bet(result="WIN", odds=2.0),
            _make_bet(result="LOSS", odds=2.0),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 2
        assert s["losses"] == 1
        assert s["total"] == 3
        # ROI: +1 +1 -1 = 1 on 3 bets → 33.3%
        assert s["win_rate"] == pytest.approx(66.7, abs=0.1)
        assert s["roi_pct"] == pytest.approx(33.3, abs=0.1)

    def test_void_bets_counted_separately(self):
        bets = [
            _make_bet(result="WIN", odds=2.0),
            _make_bet(result="VOID", odds=2.0),
            _make_bet(result="LOSS", odds=2.0),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 1
        assert s["losses"] == 1
        assert s["voids"] == 1
        assert s["total"] == 2  # VOID excluded from total resolved

    def test_pending_bets_excluded(self):
        bets = [
            _make_bet(result="WIN", odds=2.0),
            _make_bet(result="PENDING", odds=2.0),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 1
        assert s["total"] == 1


class TestCalcStatsOddsHandling:
    def test_missing_odds_falls_back_to_1_85_and_flags(self):
        bets = [_make_bet(result="WIN", odds=None)]
        s = calc_stats(bets)
        # Fallback odds = 1.85 → gain = 0.85 → roi_pct = 85
        assert s["roi_pct"] == pytest.approx(85.0)
        assert s.get("odds_estimated_count") == 1

    def test_zero_odds_treated_as_missing(self):
        bets = [_make_bet(result="LOSS", odds=0)]
        s = calc_stats(bets)
        assert s.get("odds_estimated_count") == 1

    def test_singles_threshold_at_3(self):
        # Odds exactly 3.0 = single; > 3.0 = combo
        bets = [
            _make_bet(result="WIN", odds=3.0),  # single
            _make_bet(result="WIN", odds=3.01),  # combine
        ]
        s = calc_stats(bets)
        assert s["singles_count"] == 1
        assert s["combines_count"] == 1

    def test_roi_singles_excludes_combines(self):
        bets = [
            _make_bet(result="WIN", odds=2.0),  # single, +1
            _make_bet(result="LOSS", odds=5.0),  # combine, -1 (excluded)
        ]
        s = calc_stats(bets)
        # Full ROI: (1 - 1) / 2 = 0%
        assert s["roi_pct"] == 0.0
        # Singles ROI: +1 on 1 single → 100%
        assert s["roi_singles_pct"] == 100.0

    def test_sample_warning_below_10_bets(self):
        bets = [_make_bet(result="WIN", odds=2.0) for _ in range(5)]
        s = calc_stats(bets)
        assert "sample_warning" in s
        assert "5" in s["sample_warning"]

    def test_no_sample_warning_at_10(self):
        bets = [_make_bet(result="WIN", odds=2.0) for _ in range(10)]
        s = calc_stats(bets)
        assert "sample_warning" not in s


class TestCalcStatsFunCombos:
    """FUN bets must be grouped per (date, market) and resolved as a combo."""

    def test_fun_combo_all_wins_becomes_single_win(self):
        bets = [
            _make_bet(market="fun_football", result="WIN", odds=3.0),
            _make_bet(market="fun_football", result="WIN", odds=4.0),
        ]
        s = calc_stats(bets)
        # Combined odds = 12.0 → 1 WIN (single combo)
        assert s["wins"] == 1
        assert s["losses"] == 0
        # Full ROI: 12 - 1 = 11 on 1 bet → 1100%
        assert s["roi_pct"] == pytest.approx(1100.0)
        # Combined odds > 3.0 → this is a combine, not a single
        assert s["combines_count"] == 1
        assert s["singles_count"] == 0

    def test_fun_combo_one_loss_becomes_single_loss(self):
        bets = [
            _make_bet(market="fun_football", result="WIN", odds=3.0),
            _make_bet(market="fun_football", result="LOSS", odds=4.0),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 0
        assert s["losses"] == 1

    def test_fun_combo_all_void_becomes_void(self):
        bets = [
            _make_bet(market="fun_football", result="VOID", odds=3.0),
            _make_bet(market="fun_football", result="VOID", odds=4.0),
        ]
        s = calc_stats(bets)
        # VOID combo is excluded from wins/losses but counted in voids
        assert s["wins"] == 0
        assert s["losses"] == 0
        assert s["voids"] == 1

    def test_fun_combo_void_leg_ignored_remaining_all_win(self):
        # Combo with 1 VOID leg + 1 WIN leg → the non-void legs all win → combo WIN
        bets = [
            _make_bet(market="fun_football", result="VOID", odds=3.0),
            _make_bet(market="fun_football", result="WIN", odds=4.0),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 1
        assert s["losses"] == 0

    def test_fun_combo_with_pending_leg_stays_pending(self):
        # A PENDING leg means the combo isn't resolved → not counted
        bets = [
            _make_bet(market="fun_football", result="PENDING", odds=3.0),
            _make_bet(market="fun_football", result="WIN", odds=4.0),
        ]
        s = calc_stats(bets)
        assert s["total"] == 0  # Combo remains PENDING

    def test_fun_groups_separate_by_date(self):
        bets = [
            _make_bet(market="fun_football", result="WIN", odds=3.0, date="2026-04-01"),
            _make_bet(market="fun_football", result="LOSS", odds=3.0, date="2026-04-02"),
        ]
        s = calc_stats(bets)
        # 2 distinct combos: one WIN, one LOSS
        assert s["wins"] == 1
        assert s["losses"] == 1

    def test_fun_nhl_groups_separately_from_fun_football(self):
        bets = [
            _make_bet(market="fun_football", result="WIN", odds=3.0, date="2026-04-01"),
            _make_bet(market="fun_nhl", result="LOSS", odds=3.0, date="2026-04-01"),
        ]
        s = calc_stats(bets)
        assert s["wins"] == 1
        assert s["losses"] == 1

    def test_fun_combo_falls_back_to_20x_when_all_odds_missing(self):
        # When no leg has odds, the fun combo gets fabricated odds ~20
        bets = [
            _make_bet(market="fun_football", result="WIN", odds=None),
            _make_bet(market="fun_football", result="WIN", odds=None),
        ]
        s = calc_stats(bets)
        # Combined odds = 1.0 * 1.0 = 1.0 → fallback to 20
        # ROI: 20 - 1 = 19 on 1 bet → 1900%
        assert s["roi_pct"] == pytest.approx(1900.0)


# ═══════════════════════════════════════════════════════════════════
#  build_market_breakdown
# ═══════════════════════════════════════════════════════════════════


class TestBuildMarketBreakdown:
    def test_groups_by_normalized_market(self):
        rows = [
            {
                "market": "BTTS Oui",
                "result": "WIN",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
            {
                "market": "BTTS — Les deux équipes marquent",
                "result": "LOSS",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
        ]
        breakdown = build_market_breakdown(rows)
        # Both aliases should collapse into "BTTS"
        assert set(breakdown.keys()) == {"BTTS"}
        assert breakdown["BTTS"]["total"] == 2
        assert breakdown["BTTS"]["wins"] == 1
        assert breakdown["BTTS"]["losses"] == 1

    def test_skipped_rows_excluded(self):
        rows = [
            {
                "market": "Victoire domicile",
                "result": "WIN",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
            {
                "market": "PSG vs Lyon",  # malformed → __skip__
                "result": "WIN",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
        ]
        breakdown = build_market_breakdown(rows)
        assert set(breakdown.keys()) == {"Victoire domicile"}

    def test_empty_markets_not_returned(self):
        # A market group where every bet is PENDING should not appear
        rows = [
            {
                "market": "Victoire domicile",
                "result": "PENDING",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
        ]
        breakdown = build_market_breakdown(rows)
        assert breakdown == {}

    def test_uses_match_label_fallback(self):
        # When bet_label is missing, match_label (expert_picks) is used
        rows = [
            {
                "market": "safe_football",
                "result": "WIN",
                "odds": 2.0,
                "date": "2026-04-01",
                "match_label": "PSG vs Lyon — Victoire domicile",
            },
        ]
        breakdown = build_market_breakdown(rows)
        assert "Victoire domicile" in breakdown

    def test_unknown_market_falls_back_to_raw_key(self):
        rows = [
            {
                "market": "Handicap Asiatique",
                "result": "WIN",
                "odds": 2.0,
                "date": "2026-04-01",
                "bet_label": "",
            },
        ]
        breakdown = build_market_breakdown(rows)
        # Not in MARKET_NORMALIZE → kept as-is
        assert "Handicap Asiatique" in breakdown
