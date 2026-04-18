"""Tests pour l'alerte CLV drift (ajoutée à alerting.py)."""
from __future__ import annotations

from unittest.mock import MagicMock


def test_check_clv_drift_returns_warning_if_7d_mean_below_neg1pct():
    from src.monitoring.alerting import _check_clv_drift

    # 7 rows avec CLV 1x2 moyen à -0.015 → WARNING
    rows = [{"clv_vs_pinnacle_1x2": -0.015} for _ in range(7)]
    fake = MagicMock()
    fake.table.return_value.select.return_value.gte.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = rows

    alert = _check_clv_drift(fake)
    assert alert is not None
    assert "WARNING" in alert or "CLV" in alert


def test_check_clv_drift_returns_critical_if_below_neg3pct():
    from src.monitoring.alerting import _check_clv_drift

    rows = [{"clv_vs_pinnacle_1x2": -0.04} for _ in range(7)]
    fake = MagicMock()
    fake.table.return_value.select.return_value.gte.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = rows

    alert = _check_clv_drift(fake)
    assert alert is not None
    assert "CRITICAL" in alert


def test_check_clv_drift_none_when_positive():
    from src.monitoring.alerting import _check_clv_drift

    rows = [{"clv_vs_pinnacle_1x2": 0.005} for _ in range(7)]
    fake = MagicMock()
    fake.table.return_value.select.return_value.gte.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = rows

    assert _check_clv_drift(fake) is None


def test_check_clv_drift_none_when_insufficient_data():
    from src.monitoring.alerting import _check_clv_drift

    rows = [{"clv_vs_pinnacle_1x2": -0.10}]  # 1 row
    fake = MagicMock()
    fake.table.return_value.select.return_value.gte.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = rows

    assert _check_clv_drift(fake) is None
