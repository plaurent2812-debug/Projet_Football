from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

EMPTY_METRICS = {
    "sample_size": 0,
    "accuracy": None,
    "brier": None,
    "log_loss": None,
    "ece": None,
    "roi": None,
    "clv_mean": None,
    "clv_positive_pct": None,
    "fallback_rate": None,
}

BINARY_MARKET_FIELDS = {
    "btts": ("pred_btts", "actual_btts"),
    "over_25": ("pred_over_25", "actual_over_25"),
    "over25": ("pred_over_25", "actual_over_25"),
    "over_15": ("pred_over_15", "actual_over_15"),
    "over15": ("pred_over_15", "actual_over_15"),
    "nhl_moneyline": ("pred_home", "actual_home_win"),
    "moneyline": ("pred_home", "actual_home_win"),
}

DEFAULT_SNAPSHOT_WINDOWS = (1, 7, 30, 90)
DEFAULT_SNAPSHOT_TRACKERS = (
    {
        "sport": "football",
        "market": "1x2",
        "model_name": "football_1x2",
        "model_version": "production_current",
    },
    {
        "sport": "football",
        "market": "btts",
        "model_name": "football_btts",
        "model_version": "production_current",
    },
    {
        "sport": "football",
        "market": "over_25",
        "model_name": "football_over_25",
        "model_version": "production_current",
    },
)


def _prob(value: Any) -> float | None:
    if value is None:
        return None
    try:
        prob = float(value)
    except (TypeError, ValueError):
        return None
    if prob > 1:
        prob /= 100.0
    return max(0.0, min(1.0, prob))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _round_or_none(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _roi(rows: list[dict]) -> float | None:
    total_stake = 0.0
    total_profit = 0.0
    for row in rows:
        stake = row.get("stake")
        profit = row.get("profit", row.get("pnl"))
        if stake is None or profit is None:
            continue
        try:
            stake_float = float(stake)
            profit_float = float(profit)
        except (TypeError, ValueError):
            continue
        if stake_float <= 0:
            continue
        total_stake += stake_float
        total_profit += profit_float
    if total_stake <= 0:
        return None
    return (total_profit / total_stake) * 100.0


def _clv(rows: list[dict]) -> tuple[float | None, float | None]:
    values: list[float] = []
    for row in rows:
        raw = row.get("clv_pct", row.get("clv"))
        if raw is None:
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not values:
        return None, None
    positive_pct = sum(1 for v in values if v > 0) / len(values)
    return _mean(values), positive_pct


def _fallback_rate(rows: list[dict]) -> float | None:
    values = [
        row.get("ml_fallback_used") for row in rows if row.get("ml_fallback_used") is not None
    ]
    if not values:
        return None
    return sum(1 for value in values if bool(value)) / len(values)


def _ece(
    records: list[tuple[float, bool]], *, n_bins: int = 10, min_samples: int = 10
) -> float | None:
    if len(records) < min_samples:
        return None
    total = len(records)
    error = 0.0
    for idx in range(n_bins):
        lo = idx / n_bins
        hi = (idx + 1) / n_bins
        bucket = [
            (confidence, correct)
            for confidence, correct in records
            if lo <= confidence < hi or (idx == n_bins - 1 and confidence == hi)
        ]
        if not bucket:
            continue
        avg_confidence = sum(confidence for confidence, _ in bucket) / len(bucket)
        accuracy = sum(1 for _, correct in bucket if correct) / len(bucket)
        error += (len(bucket) / total) * abs(avg_confidence - accuracy)
    return error


def _compute_1x2(rows: list[dict]) -> dict:
    briers: list[float] = []
    losses: list[float] = []
    correct_count = 0
    records: list[tuple[float, bool]] = []

    for row in rows:
        actual = row.get("actual_result")
        home = _prob(row.get("pred_home"))
        draw = _prob(row.get("pred_draw"))
        away = _prob(row.get("pred_away"))
        if actual not in {"H", "D", "A"} or home is None or draw is None or away is None:
            continue

        probs = {"H": home, "D": draw, "A": away}
        predicted = max(probs, key=probs.get)
        correct = predicted == actual
        correct_count += int(correct)
        confidence = probs[predicted]
        records.append((confidence, correct))

        outcomes = {
            "H": 1.0 if actual == "H" else 0.0,
            "D": 1.0 if actual == "D" else 0.0,
            "A": 1.0 if actual == "A" else 0.0,
        }
        briers.append(sum((probs[key] - outcomes[key]) ** 2 for key in ("H", "D", "A")) / 3.0)
        losses.append(-math.log(max(probs[actual], 1e-15)))

    sample_size = len(briers)
    if sample_size == 0:
        return EMPTY_METRICS.copy()

    return {
        "sample_size": sample_size,
        "accuracy": correct_count / sample_size,
        "brier": _mean(briers),
        "log_loss": _mean(losses),
        "ece": _ece(records),
        "roi": _roi(rows),
        "clv_mean": _clv(rows)[0],
        "clv_positive_pct": _clv(rows)[1],
        "fallback_rate": _fallback_rate(rows),
    }


def _compute_binary(rows: list[dict], pred_field: str, actual_field: str) -> dict:
    briers: list[float] = []
    losses: list[float] = []
    correct_count = 0
    records: list[tuple[float, bool]] = []

    for row in rows:
        probability = _prob(row.get(pred_field))
        actual_raw = row.get(actual_field)
        if probability is None or actual_raw is None:
            continue
        actual = bool(actual_raw)
        predicted = probability >= 0.5
        correct = predicted == actual
        correct_count += int(correct)
        confidence = probability if predicted else 1 - probability
        records.append((confidence, correct))

        outcome = 1.0 if actual else 0.0
        briers.append((probability - outcome) ** 2)
        losses.append(-math.log(max(probability if actual else 1 - probability, 1e-15)))

    sample_size = len(briers)
    if sample_size == 0:
        return EMPTY_METRICS.copy()

    return {
        "sample_size": sample_size,
        "accuracy": correct_count / sample_size,
        "brier": _mean(briers),
        "log_loss": _mean(losses),
        "ece": _ece(records),
        "roi": _roi(rows),
        "clv_mean": _clv(rows)[0],
        "clv_positive_pct": _clv(rows)[1],
        "fallback_rate": _fallback_rate(rows),
    }


def compute_market_metrics(rows: list[dict], market: str) -> dict:
    """Compute core model-performance metrics for one market.

    Inputs are intentionally plain dicts so this function stays easy to test
    and can be reused by API endpoints, Trigger.dev jobs, or local scripts.
    """
    if not rows:
        return EMPTY_METRICS.copy()

    normalized_market = market.lower()
    if normalized_market in {"1x2", "football_1x2"}:
        metrics = _compute_1x2(rows)
    else:
        pred_field, actual_field = BINARY_MARKET_FIELDS.get(
            normalized_market,
            ("pred_probability", "actual_bool"),
        )
        metrics = _compute_binary(rows, pred_field, actual_field)

    return {
        "sample_size": metrics["sample_size"],
        "accuracy": _round_or_none(metrics["accuracy"]),
        "brier": _round_or_none(metrics["brier"]),
        "log_loss": _round_or_none(metrics["log_loss"]),
        "ece": _round_or_none(metrics["ece"]),
        "roi": _round_or_none(metrics["roi"]),
        "clv_mean": _round_or_none(metrics["clv_mean"]),
        "clv_positive_pct": _round_or_none(metrics["clv_positive_pct"]),
        "fallback_rate": _round_or_none(metrics["fallback_rate"]),
    }


def build_performance_snapshot_from_rows(
    rows: list[dict],
    *,
    sport: str,
    market: str,
    model_name: str,
    model_version: str,
    window_days: int,
    recorded_at: datetime | None = None,
) -> dict:
    metrics = compute_market_metrics(rows, market=market)
    valid_sample_size = metrics["sample_size"]
    data_completeness_pct = valid_sample_size / len(rows) if rows else None
    snapshot = {
        "sport": sport,
        "market": market,
        "model_name": model_name,
        "model_version": model_version,
        "window_days": window_days,
        "sample_size": metrics["sample_size"],
        "accuracy": metrics["accuracy"],
        "brier": metrics["brier"],
        "log_loss": metrics["log_loss"],
        "ece": metrics["ece"],
        "roi": metrics["roi"],
        "clv_mean": metrics["clv_mean"],
        "clv_positive_pct": metrics["clv_positive_pct"],
        "fallback_rate": metrics["fallback_rate"],
        "data_completeness_pct": _round_or_none(data_completeness_pct),
        "metrics": metrics,
    }
    if recorded_at is not None:
        snapshot["recorded_at"] = recorded_at.isoformat()
    return snapshot


def _resolve_supabase_client(supabase_client: Any | None) -> Any:
    if supabase_client is not None:
        return supabase_client
    from src.config import supabase

    return supabase


def _fetch_prediction_rows(
    supabase_client: Any,
    *,
    tracker: dict,
    since: datetime,
) -> list[dict]:
    query = (
        supabase_client.table("prediction_results")
        .select("*")
        .not_.is_("actual_result", "null")
        .gte("created_at", since.isoformat())
    )
    model_version = tracker.get("model_version")
    if model_version and model_version != "production_current":
        query = query.eq("model_version", model_version)
    return query.execute().data or []


def persist_daily_performance_snapshots(
    *,
    supabase_client: Any | None = None,
    windows: list[int] | tuple[int, ...] | None = None,
    trackers: list[dict] | tuple[dict, ...] | None = None,
    now: datetime | None = None,
) -> dict:
    """Compute and persist daily model-performance snapshots."""
    client = _resolve_supabase_client(supabase_client)
    recorded_at = now or datetime.now(timezone.utc)
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    window_days = list(windows or DEFAULT_SNAPSHOT_WINDOWS)
    tracked_markets = list(trackers or DEFAULT_SNAPSHOT_TRACKERS)

    snapshots: list[dict] = []
    market_summaries: list[dict] = []
    for tracker in tracked_markets:
        for window in window_days:
            since = recorded_at - timedelta(days=window)
            rows = _fetch_prediction_rows(client, tracker=tracker, since=since)
            snapshot = build_performance_snapshot_from_rows(
                rows,
                sport=tracker["sport"],
                market=tracker["market"],
                model_name=tracker["model_name"],
                model_version=tracker["model_version"],
                window_days=window,
                recorded_at=recorded_at,
            )
            snapshots.append(snapshot)
            market_summaries.append(
                {
                    "sport": snapshot["sport"],
                    "market": snapshot["market"],
                    "sample_size": snapshot["sample_size"],
                }
            )

    if snapshots:
        client.table("model_performance_snapshots").insert(snapshots).execute()

    return {"inserted": len(snapshots), "windows": window_days, "markets": market_summaries}
