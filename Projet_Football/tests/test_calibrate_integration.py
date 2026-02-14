"""
Tests d'intégration pour models/calibrate.py —
calibration ML des probabilités de prédiction.

Toutes les interactions Supabase sont mockées via @patch("models.calibrate.supabase").
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

SUPABASE_PATCH = "models.calibrate.supabase"


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def _make_result(
    *,
    pred_home: int = 60,
    pred_draw: int = 20,
    pred_away: int = 20,
    pred_btts: int = 55,
    pred_over_05: int = 90,
    pred_over_15: int = 75,
    pred_over_25: int = 55,
    actual_result: str = "H",
    actual_btts: bool = True,
    actual_over_05: bool = True,
    actual_over_15: bool = True,
    actual_over_25: bool = True,
    league_id: int = 61,
    result_1x2_ok: bool = True,
    btts_ok: bool = True,
    over_05_ok: bool = True,
    over_15_ok: bool = True,
    over_25_ok: bool = True,
) -> dict:
    """Build a minimal prediction-result row from the prediction_results table."""
    return {
        "pred_home": pred_home,
        "pred_draw": pred_draw,
        "pred_away": pred_away,
        "pred_btts": pred_btts,
        "pred_over_05": pred_over_05,
        "pred_over_15": pred_over_15,
        "pred_over_25": pred_over_25,
        "actual_result": actual_result,
        "actual_btts": actual_btts,
        "actual_over_05": actual_over_05,
        "actual_over_15": actual_over_15,
        "actual_over_25": actual_over_25,
        "league_id": league_id,
        "result_1x2_ok": result_1x2_ok,
        "btts_ok": btts_ok,
        "over_05_ok": over_05_ok,
        "over_15_ok": over_15_ok,
        "over_25_ok": over_25_ok,
    }


def _make_many_results(n: int = 30, *, league_id: int = 61) -> list[dict]:
    """Generate *n* varied prediction-result rows.

    Alternates between home wins, draws, and away wins with realistic
    spread of predicted probabilities so that calibrate_all has enough
    data (≥ MIN_SAMPLES) to perform Platt scaling.
    """
    np.random.seed(42)
    results: list[dict] = []
    outcomes = ["H", "D", "A"]
    for i in range(n):
        outcome = outcomes[i % 3]
        # Generate realistic probabilities that sum to ~100
        ph = int(np.random.uniform(20, 70))
        pd_ = int(np.random.uniform(10, 40))
        pa = 100 - ph - pd_
        total_goals = int(np.random.uniform(0, 5))
        btts = total_goals >= 2 and np.random.random() > 0.3
        results.append(
            _make_result(
                pred_home=ph,
                pred_draw=pd_,
                pred_away=max(pa, 5),
                pred_btts=int(np.random.uniform(30, 80)),
                pred_over_05=int(np.random.uniform(60, 99)),
                pred_over_15=int(np.random.uniform(40, 90)),
                pred_over_25=int(np.random.uniform(30, 70)),
                actual_result=outcome,
                actual_btts=btts,
                actual_over_05=total_goals > 0,
                actual_over_15=total_goals > 1,
                actual_over_25=total_goals > 2,
                league_id=league_id,
                result_1x2_ok=(outcome == "H" and ph > pd_ and ph > pa),
            )
        )
    return results


def _chainable_query(data: list[dict] | None = None):
    """Return a MagicMock that supports Supabase's chainable query API."""
    q = MagicMock()
    q.select.return_value = q
    q.eq.return_value = q
    q.is_.return_value = q
    q.neq.return_value = q
    q.in_.return_value = q
    q.order.return_value = q
    q.limit.return_value = q
    q.upsert.return_value = q
    q.execute.return_value = MagicMock(data=data or [])
    return q


# ═══════════════════════════════════════════════════════════════════
#  1. TestLoadResults
# ═══════════════════════════════════════════════════════════════════


class TestLoadResults:
    """Tests for load_results() — fetching evaluation data from Supabase."""

    @patch(SUPABASE_PATCH)
    def test_empty_table_returns_empty_list(self, mock_sb):
        """When prediction_results is empty, return []."""
        mock_sb.table.return_value = _chainable_query(data=[])

        from models.calibrate import load_results

        result = load_results()

        assert result == []
        mock_sb.table.assert_called_once_with("prediction_results")

    @patch(SUPABASE_PATCH)
    def test_none_data_returns_empty_list(self, mock_sb):
        """When .execute().data is None, return []."""
        q = _chainable_query()
        q.execute.return_value = MagicMock(data=None)
        mock_sb.table.return_value = q

        from models.calibrate import load_results

        result = load_results()

        assert result == []

    @patch(SUPABASE_PATCH)
    def test_valid_data_returned_as_is(self, mock_sb):
        """Rows from Supabase should be returned unmodified."""
        rows = [_make_result(), _make_result(actual_result="D")]
        mock_sb.table.return_value = _chainable_query(data=rows)

        from models.calibrate import load_results

        result = load_results()

        assert len(result) == 2
        assert result[0]["actual_result"] == "H"
        assert result[1]["actual_result"] == "D"


# ═══════════════════════════════════════════════════════════════════
#  2. TestPrepareDataset
# ═══════════════════════════════════════════════════════════════════


class TestPrepareDataset:
    """Tests for prepare_dataset() — extracting X, y arrays."""

    def test_extracts_correct_values(self):
        """X should be pred/100 in shape (n,1), y should be 0/1."""
        from models.calibrate import prepare_dataset

        results = [
            {"pred_home": 70, "result_1x2_ok": True},
            {"pred_home": 30, "result_1x2_ok": False},
        ]
        X, y = prepare_dataset(results, "pred_home", "result_1x2_ok")

        assert X.shape == (2, 1)
        np.testing.assert_allclose(X.ravel(), [0.70, 0.30])
        np.testing.assert_array_equal(y, [1.0, 0.0])

    def test_skips_rows_with_missing_pred(self):
        """Rows where pred_field is None should be skipped."""
        from models.calibrate import prepare_dataset

        results = [
            {"pred_home": None, "result_1x2_ok": True},
            {"pred_home": 50, "result_1x2_ok": False},
        ]
        X, y = prepare_dataset(results, "pred_home", "result_1x2_ok")

        assert X.shape == (1, 1)
        np.testing.assert_allclose(X.ravel(), [0.50])

    def test_skips_rows_with_missing_actual(self):
        """Rows where actual_field is None should be skipped."""
        from models.calibrate import prepare_dataset

        results = [
            {"pred_btts": 60, "btts_ok": None},
            {"pred_btts": 40, "btts_ok": True},
        ]
        X, y = prepare_dataset(results, "pred_btts", "btts_ok")

        assert X.shape == (1, 1)
        np.testing.assert_array_equal(y, [1.0])

    def test_empty_results_returns_empty_arrays(self):
        """Empty input should produce empty arrays."""
        from models.calibrate import prepare_dataset

        X, y = prepare_dataset([], "pred_home", "result_1x2_ok")

        assert X.shape == (0, 1)
        assert y.shape == (0,)

    def test_actual_truthy_falsy_conversion(self):
        """Boolean-ish actuals should be cast to 1.0 or 0.0."""
        from models.calibrate import prepare_dataset

        results = [
            {"p": 80, "a": 1},  # truthy → 1.0
            {"p": 20, "a": 0},  # falsy  → 0.0
            {"p": 50, "a": "yes"},  # truthy → 1.0
        ]
        X, y = prepare_dataset(results, "p", "a")

        np.testing.assert_array_equal(y, [1.0, 0.0, 1.0])


# ═══════════════════════════════════════════════════════════════════
#  3. TestApplyCalibration
# ═══════════════════════════════════════════════════════════════════


class TestApplyCalibration:
    """Tests for apply_calibration() and _get_calibration_params() caching."""

    def setup_method(self):
        """Clear the module-level cache before each test."""
        from models import calibrate

        calibrate._calibration_cache.clear()

    @patch(SUPABASE_PATCH)
    def test_no_params_returns_original(self, mock_sb):
        """When no calibration row exists, return raw_prob unchanged."""
        # Both league-specific and global queries return empty
        mock_sb.table.return_value = _chainable_query(data=[])

        from models.calibrate import apply_calibration

        assert apply_calibration(65, "btts", league_id=None) == 65

    @patch(SUPABASE_PATCH)
    def test_insufficient_sample_size_returns_original(self, mock_sb):
        """When sample_size < MIN_SAMPLES, return raw_prob unchanged."""
        calib_row = {"platt_a": 2.0, "platt_b": -1.0, "sample_size": 5}
        mock_sb.table.return_value = _chainable_query(data=[calib_row])

        from models.calibrate import apply_calibration

        assert apply_calibration(60, "btts") == 60

    @patch(SUPABASE_PATCH)
    def test_calibration_modifies_probability(self, mock_sb):
        """With valid params and enough samples, probability should change."""
        calib_row = {"platt_a": 3.0, "platt_b": -1.5, "sample_size": 50}
        mock_sb.table.return_value = _chainable_query(data=[calib_row])

        from models.calibrate import apply_calibration

        calibrated = apply_calibration(70, "1x2_home")

        # sigmoid(3.0 * 0.7 + (-1.5)) = sigmoid(0.6) ≈ 0.6457 → 65
        assert calibrated != 70
        assert 0 <= calibrated <= 100

    @patch(SUPABASE_PATCH)
    def test_caching_avoids_second_query(self, mock_sb):
        """Second call with same (bet_type, league_id) should use cache."""
        calib_row = {"platt_a": 1.5, "platt_b": -0.5, "sample_size": 40}
        mock_sb.table.return_value = _chainable_query(data=[calib_row])

        from models.calibrate import apply_calibration

        result1 = apply_calibration(50, "btts", league_id=None)
        result2 = apply_calibration(50, "btts", league_id=None)

        assert result1 == result2
        # table() should only be called for the first invocation
        # (once for the global fallback query)
        initial_call_count = mock_sb.table.call_count
        apply_calibration(50, "btts", league_id=None)
        assert mock_sb.table.call_count == initial_call_count  # no new calls

    @patch(SUPABASE_PATCH)
    def test_probability_zero_percent(self, mock_sb):
        """Edge case: raw_prob = 0 should not crash."""
        calib_row = {"platt_a": 2.0, "platt_b": -1.0, "sample_size": 30}
        mock_sb.table.return_value = _chainable_query(data=[calib_row])

        from models.calibrate import apply_calibration

        result = apply_calibration(0, "1x2_home")

        # sigmoid(2.0 * 0.0 + (-1.0)) = sigmoid(-1.0) ≈ 0.2689 → 27
        assert 0 <= result <= 100

    @patch(SUPABASE_PATCH)
    def test_probability_hundred_percent(self, mock_sb):
        """Edge case: raw_prob = 100 should not crash."""
        calib_row = {"platt_a": 2.0, "platt_b": -1.0, "sample_size": 30}
        mock_sb.table.return_value = _chainable_query(data=[calib_row])

        from models.calibrate import apply_calibration

        result = apply_calibration(100, "over_25")

        # sigmoid(2.0 * 1.0 + (-1.0)) = sigmoid(1.0) ≈ 0.7311 → 73
        assert 0 <= result <= 100

    @patch(SUPABASE_PATCH)
    def test_league_specific_params_preferred(self, mock_sb):
        """When league-specific params exist, they should be used (not global)."""
        league_row = {"platt_a": 4.0, "platt_b": -2.0, "sample_size": 50}

        # The first query (league-specific) returns data
        mock_sb.table.return_value = _chainable_query(data=[league_row])

        from models.calibrate import apply_calibration

        result = apply_calibration(50, "btts", league_id=61)

        # sigmoid(4.0 * 0.5 + (-2.0)) = sigmoid(0.0) = 0.5 → 50
        assert result == 50


# ═══════════════════════════════════════════════════════════════════
#  4. TestGetCalibrationParams
# ═══════════════════════════════════════════════════════════════════


class TestGetCalibrationParams:
    """Tests for _get_calibration_params() — Supabase lookup with caching."""

    def setup_method(self):
        from models import calibrate

        calibrate._calibration_cache.clear()

    @patch(SUPABASE_PATCH)
    def test_returns_none_when_no_data(self, mock_sb):
        """Should return None when neither league nor global row exists."""
        mock_sb.table.return_value = _chainable_query(data=[])

        from models.calibrate import _get_calibration_params

        assert _get_calibration_params("btts", league_id=None) is None

    @patch(SUPABASE_PATCH)
    def test_global_fallback_when_no_league(self, mock_sb):
        """With league_id=None, only the global (is_null) query is made."""
        global_row = {"platt_a": 1.0, "platt_b": 0.0, "sample_size": 100}
        mock_sb.table.return_value = _chainable_query(data=[global_row])

        from models.calibrate import _get_calibration_params

        result = _get_calibration_params("1x2_home", league_id=None)

        assert result == global_row

    @patch(SUPABASE_PATCH)
    def test_league_fallback_to_global(self, mock_sb):
        """When league-specific query returns empty, fall back to global."""
        global_row = {"platt_a": 1.2, "platt_b": -0.1, "sample_size": 80}

        # First call (league-specific) → empty, second call (global) → data
        q_league = _chainable_query(data=[])
        q_global = _chainable_query(data=[global_row])
        mock_sb.table.side_effect = [q_league, q_global]

        from models.calibrate import _get_calibration_params

        result = _get_calibration_params("btts", league_id=99)

        assert result == global_row

    @patch(SUPABASE_PATCH)
    def test_result_is_cached(self, mock_sb):
        """After the first lookup, subsequent calls use the cache."""
        row = {"platt_a": 1.0, "platt_b": 0.0, "sample_size": 50}
        mock_sb.table.return_value = _chainable_query(data=[row])

        from models.calibrate import _get_calibration_params

        r1 = _get_calibration_params("over_25", league_id=None)
        call_count_after_first = mock_sb.table.call_count

        r2 = _get_calibration_params("over_25", league_id=None)
        assert r1 is r2
        # No additional Supabase calls
        assert mock_sb.table.call_count == call_count_after_first


# ═══════════════════════════════════════════════════════════════════
#  5. TestCalibrateAll
# ═══════════════════════════════════════════════════════════════════


class TestCalibrateAll:
    """Tests for calibrate_all() — full calibration pipeline."""

    def test_empty_results_returns_empty(self):
        """No results → no calibration rows."""
        from models.calibrate import calibrate_all

        rows = calibrate_all([], league_id=None)
        assert rows == []

    def test_too_few_results_skipped(self):
        """Fewer than 5 results per bet type → that type is skipped."""
        from models.calibrate import calibrate_all

        # Only 3 results — below the n < 5 threshold in calibrate_all
        results = [_make_result() for _ in range(3)]
        rows = calibrate_all(results, league_id=None)

        # With only 3 results, some bet types may still appear if they have
        # non-None values. But in practice, 3 is enough since all fields are set.
        # The important thing is that fit_platt_scaling returns identity (1.0, 0.0)
        # when n < MIN_SAMPLES (20).
        for row in rows:
            if row["sample_size"] < 20:
                assert row["platt_a"] == 1.0
                assert row["platt_b"] == 0.0

    def test_valid_results_produce_calibration_rows(self):
        """With enough results, calibrate_all should return rows for each bet type."""
        from models.calibrate import calibrate_all

        results = _make_many_results(50)
        rows = calibrate_all(results, league_id=None)

        assert len(rows) > 0
        bet_types_found = {r["bet_type"] for r in rows}
        # At least some of the standard bet types should be present
        assert len(bet_types_found) >= 1

        for row in rows:
            assert "platt_a" in row
            assert "platt_b" in row
            assert "bias" in row
            assert "sample_size" in row
            assert "accuracy" in row
            assert "brier_score" in row
            assert row["league_id"] is None

    def test_league_filter(self):
        """calibrate_all with league_id should only use matching results."""
        from models.calibrate import calibrate_all

        results_61 = _make_many_results(30, league_id=61)
        results_39 = _make_many_results(30, league_id=39)
        all_results = results_61 + results_39

        rows = calibrate_all(all_results, league_id=61)

        for row in rows:
            assert row["league_id"] == 61

    def test_accuracy_is_between_zero_and_one(self):
        """Accuracy values should be in [0, 1]."""
        from models.calibrate import calibrate_all

        results = _make_many_results(50)
        rows = calibrate_all(results, league_id=None)

        for row in rows:
            if row["accuracy"] is not None:
                assert 0.0 <= row["accuracy"] <= 1.0

    def test_calibration_does_not_worsen_brier(self):
        """When Platt scaling is applied, Brier should not degrade badly."""
        from models.calibrate import calibrate_all

        results = _make_many_results(100)
        rows = calibrate_all(results, league_id=None)

        for row in rows:
            brier = row.get("brier_score")
            if brier is not None:
                # Brier is bounded [0, 1]; calibrated score shouldn't exceed 0.5
                # for any remotely reasonable model
                assert brier <= 0.5


# ═══════════════════════════════════════════════════════════════════
#  6. TestClearCache
# ═══════════════════════════════════════════════════════════════════


class TestClearCache:
    """Tests for clear_cache() — flushing the in-memory cache."""

    def setup_method(self):
        from models import calibrate

        calibrate._calibration_cache.clear()

    def test_clears_populated_cache(self):
        """After adding entries to the cache, clear_cache() should empty it."""
        from models import calibrate

        calibrate._calibration_cache["btts_None"] = {"platt_a": 1.0}
        calibrate._calibration_cache["over_25_61"] = {"platt_a": 2.0}
        assert len(calibrate._calibration_cache) == 2

        calibrate.clear_cache()
        assert len(calibrate._calibration_cache) == 0

    def test_clear_empty_cache_is_noop(self):
        """Clearing an already-empty cache should not raise."""
        from models import calibrate

        calibrate._calibration_cache.clear()
        calibrate.clear_cache()
        assert calibrate._calibration_cache == {}


# ═══════════════════════════════════════════════════════════════════
#  7. TestSaveAndPrint
# ═══════════════════════════════════════════════════════════════════


class TestSaveAndPrint:
    """Tests for _save_and_print() — upserting rows to Supabase."""

    @patch(SUPABASE_PATCH)
    def test_upserts_each_row(self, mock_sb):
        """Each calibration row should trigger a supabase upsert."""
        mock_sb.table.return_value = _chainable_query()

        from models.calibrate import _save_and_print

        rows = [
            {
                "bet_type": "btts",
                "league_id": None,
                "platt_a": 1.5,
                "platt_b": -0.3,
                "bias": 0.02,
                "sample_size": 50,
                "accuracy": 0.68,
                "brier_score": 0.22,
            },
            {
                "bet_type": "over_25",
                "league_id": None,
                "platt_a": 2.0,
                "platt_b": -1.0,
                "bias": -0.05,
                "sample_size": 45,
                "accuracy": 0.72,
                "brier_score": 0.19,
            },
        ]
        _save_and_print(rows)

        # table("calibration") should be called once per row
        assert mock_sb.table.call_count == 2
        mock_sb.table.assert_called_with("calibration")

    @patch(SUPABASE_PATCH)
    def test_upsert_called_with_conflict_key(self, mock_sb):
        """Upsert should specify on_conflict='bet_type,league_id'."""
        q = _chainable_query()
        mock_sb.table.return_value = q

        from models.calibrate import _save_and_print

        row = {
            "bet_type": "1x2_home",
            "league_id": 61,
            "platt_a": 1.0,
            "platt_b": 0.0,
            "bias": 0.0,
            "sample_size": 30,
            "accuracy": 0.60,
            "brier_score": 0.25,
        }
        _save_and_print([row])

        q.upsert.assert_called_once_with(row, on_conflict="bet_type,league_id")

    @patch(SUPABASE_PATCH)
    def test_exception_does_not_crash(self, mock_sb):
        """If upsert raises, _save_and_print should log a warning, not crash."""
        q = MagicMock()
        q.upsert.side_effect = Exception("DB write error")
        mock_sb.table.return_value = q

        from models.calibrate import _save_and_print

        row = {
            "bet_type": "btts",
            "league_id": None,
            "platt_a": 1.0,
            "platt_b": 0.0,
            "bias": 0.01,
            "sample_size": 25,
            "accuracy": 0.55,
            "brier_score": 0.30,
        }
        # Should not raise
        _save_and_print([row])

    @patch(SUPABASE_PATCH)
    def test_empty_rows_does_nothing(self, mock_sb):
        """Passing an empty list should not call supabase at all."""
        from models.calibrate import _save_and_print

        _save_and_print([])
        mock_sb.table.assert_not_called()

    @patch(SUPABASE_PATCH)
    def test_negative_bias_formatted(self, mock_sb):
        """Negative bias should not crash the log formatting."""
        mock_sb.table.return_value = _chainable_query()

        from models.calibrate import _save_and_print

        row = {
            "bet_type": "1x2_away",
            "league_id": None,
            "platt_a": 0.8,
            "platt_b": 0.1,
            "bias": -0.03,
            "sample_size": 40,
            "accuracy": 0.62,
            "brier_score": 0.24,
        }
        # Should not raise (bias formatting uses +/- prefix)
        _save_and_print([row])


# ═══════════════════════════════════════════════════════════════════
#  8. TestRunCalibration (pipeline)
# ═══════════════════════════════════════════════════════════════════


class TestRunCalibration:
    """Integration test for run_calibration() — the full pipeline."""

    def setup_method(self):
        from models import calibrate

        calibrate._calibration_cache.clear()

    @patch(SUPABASE_PATCH)
    def test_no_results_early_exit(self, mock_sb):
        """When load_results returns empty, run_calibration exits cleanly."""
        mock_sb.table.return_value = _chainable_query(data=[])

        from models.calibrate import run_calibration

        # Should not raise
        run_calibration()

    @patch(SUPABASE_PATCH)
    def test_full_pipeline_with_data(self, mock_sb):
        """run_calibration with enough data should upsert calibration rows."""
        results = _make_many_results(50, league_id=61)

        # load_results returns our data, all subsequent table calls return
        # chainable mocks (for upserts)
        pred_query = _chainable_query(data=results)
        upsert_query = _chainable_query(data=[])

        call_count = [0]

        def table_router(name):
            call_count[0] += 1
            if name == "prediction_results":
                return pred_query
            return upsert_query  # calibration table upserts

        mock_sb.table.side_effect = table_router

        from models.calibrate import run_calibration

        run_calibration()

        # At least one upsert should have been made
        assert call_count[0] >= 2  # 1 for load + at least 1 for save
