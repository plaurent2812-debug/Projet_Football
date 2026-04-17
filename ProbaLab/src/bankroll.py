"""
bankroll.py — Gestion du bankroll et suivi des paris.

Gère l'enregistrement des paris, le calcul du bankroll,
la résolution des résultats et les statistiques P&L.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.config import logger, supabase

# ═══════════════════════════════════════════════════════════════════
#  CONSTANTES
# ═══════════════════════════════════════════════════════════════════

DEFAULT_BANKROLL: float = 500.0
TABLE: str = "bankroll_tracking"


# ═══════════════════════════════════════════════════════════════════
#  LECTURE DU BANKROLL ACTUEL
# ═══════════════════════════════════════════════════════════════════


def get_current_bankroll() -> float:
    """Retrieve the current bankroll from the latest entry.

    Returns:
        Current bankroll amount, or :data:`DEFAULT_BANKROLL` if no
        entries exist yet.
    """
    try:
        data = (
            supabase.table(TABLE)
            .select("bankroll_after")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if data and data[0].get("bankroll_after") is not None:
            return float(data[0]["bankroll_after"])
    except Exception as e:
        logger.warning("Impossible de lire le bankroll: %s", e)
    return DEFAULT_BANKROLL


# ═══════════════════════════════════════════════════════════════════
#  ENREGISTREMENT D'UN PARI
# ═══════════════════════════════════════════════════════════════════


def place_bet(
    ticket_type: str,
    stake: float,
    odds: float,
    description: str = "",
    fixture_ids: list[int] | None = None,
    model_version: str = "hybrid_v3",
) -> dict[str, Any]:
    """Record a new bet in the bankroll tracking table.

    Uses a PostgreSQL RPC function (``place_bet_atomic``) to guarantee
    atomicity via ``SELECT … FOR UPDATE`` row-level locking.  Falls back
    to the legacy read-then-write loop when the RPC is not available
    (e.g. migration not yet applied).

    Args:
        ticket_type: ``"safe"``, ``"fun"``, ``"jackpot"``, or ``"single"``.
        stake: Bet amount.
        odds: Combined decimal odds.
        description: Human-readable description of the bet.
        fixture_ids: List of related fixture IDs.
        model_version: Model version used for the prediction.

    Returns:
        The inserted row as a dict.
    """
    if stake < 0.50:
        logger.info("Stake %.2f€ below minimum (0.50€), skipping bet", stake)
        return {"status": "skipped", "reason": "stake_below_minimum"}

    # ── Atomic path via Supabase RPC ──────────────────────────────
    try:
        result = supabase.rpc(
            "place_bet_atomic",
            {
                "p_ticket_type": ticket_type,
                "p_stake": round(stake, 2),
                "p_odds": round(odds, 3),
                "p_description": description,
                "p_fixture_ids": fixture_ids or [],
                "p_model_version": model_version,
            },
        ).execute()

        data = result.data
        if isinstance(data, list) and len(data) == 1:
            data = data[0]

        if data and isinstance(data, dict):
            if "error" in data:
                logger.warning("Bet rejected by RPC: %s", data["error"])
                return data
            logger.info(
                "Pari enregistré (atomic): %s — %.2f€ @ %.2f (potentiel: %.2f€)",
                ticket_type,
                stake,
                odds,
                stake * odds,
            )
            return data
    except Exception:
        logger.warning("place_bet_atomic RPC failed — falling back to legacy", exc_info=True)

    # ── Fallback: legacy non-atomic path ──────────────────────────
    return _place_bet_legacy(ticket_type, stake, odds, description, fixture_ids, model_version)


def _place_bet_legacy(
    ticket_type: str,
    stake: float,
    odds: float,
    description: str = "",
    fixture_ids: list[int] | None = None,
    model_version: str = "hybrid_v3",
) -> dict[str, Any]:
    """Legacy non-atomic bet placement (read-then-write with retry).

    Kept as fallback in case the ``place_bet_atomic`` RPC is not yet
    deployed.  Subject to race conditions under concurrent writes.
    """
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        current = get_current_bankroll()

        if stake > current:
            logger.warning("Mise (%.2f) > bankroll (%.2f) — pari refusé", stake, current)
            return {"error": "Stake exceeds bankroll"}

        row: dict[str, Any] = {
            "date": datetime.now(timezone.utc).date().isoformat(),
            "ticket_type": ticket_type,
            "bet_description": description,
            "stake": round(stake, 2),
            "odds": round(odds, 3),
            "potential_gain": round(stake * odds, 2),
            "actual_gain": 0,
            "status": "pending",
            "bankroll_before": round(current, 2),
            "bankroll_after": round(current - stake, 2),
            "model_version": model_version,
            "fixture_ids": fixture_ids or [],
        }

        try:
            result = supabase.table(TABLE).insert(row).execute()

            # Verify bankroll didn't change between read and insert
            # (optimistic concurrency: re-read and confirm)
            fresh = get_current_bankroll()
            expected_after = round(current - stake, 2)
            if abs(fresh - expected_after) > 0.01 and attempt < MAX_RETRIES - 1:
                inserted_id = result.data[0].get("id") if result.data else None
                if inserted_id:
                    supabase.table(TABLE).delete().eq("id", inserted_id).execute()
                logger.warning(
                    "Bankroll concurrent modification detected, retrying (%d/%d)",
                    attempt + 1,
                    MAX_RETRIES,
                )
                continue

            logger.info(
                "Pari enregistré (legacy): %s — %.2f€ @ %.2f (potentiel: %.2f€)",
                ticket_type,
                stake,
                odds,
                stake * odds,
            )
            return result.data[0] if result.data else row
        except Exception as e:
            logger.exception("Erreur enregistrement pari")
            return {"error": str(e)}

    return {"error": "Failed after max retries (concurrent bankroll modifications)"}


# ═══════════════════════════════════════════════════════════════════
#  RÉSOLUTION D'UN PARI
# ═══════════════════════════════════════════════════════════════════


def resolve_bet(bet_id: int, won: bool) -> dict[str, Any]:
    """Resolve a pending bet and update the bankroll.

    Args:
        bet_id: ID of the bet to resolve.
        won: ``True`` if the bet was successful, ``False`` otherwise.

    Returns:
        The updated row as a dict.
    """
    try:
        # Récupérer le pari
        data = supabase.table(TABLE).select("*").eq("id", bet_id).execute().data
        if not data:
            return {"error": f"Bet {bet_id} not found"}

        bet = data[0]
        if bet["status"] != "pending":
            return {"error": f"Bet {bet_id} already resolved ({bet['status']})"}

        stake = float(bet["stake"])
        odds = float(bet["odds"]) if bet["odds"] else 1.0
        bankroll_before = float(bet["bankroll_before"])

        if won:
            actual_gain = round(stake * odds - stake, 2)  # Net profit
            bankroll_after = round(bankroll_before + stake * odds - stake, 2)
            # Actually: bankroll = bankroll_before (before deduction) - stake + winnings
            # Since bankroll_before already had the stake, we add it back + profit
            bankroll_after = round(float(bet["bankroll_after"]) + stake * odds, 2)
            status = "won"
        else:
            actual_gain = round(-stake, 2)
            bankroll_after = float(bet["bankroll_after"])  # Stake already deducted
            status = "lost"

        roi = round(actual_gain / stake, 4) if stake > 0 else 0

        update: dict[str, Any] = {
            "status": status,
            "actual_gain": actual_gain,
            "bankroll_after": bankroll_after,
            "roi": roi,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }

        result = supabase.table(TABLE).update(update).eq("id", bet_id).execute()
        logger.info(
            "Pari #%d résolu: %s — gain: %.2f€ — bankroll: %.2f€",
            bet_id,
            status,
            actual_gain,
            bankroll_after,
        )
        return result.data[0] if result.data else update

    except Exception as e:
        logger.exception("Erreur résolution pari #%d", bet_id)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════
#  STATISTIQUES P&L
# ═══════════════════════════════════════════════════════════════════


def get_pnl_summary() -> dict[str, Any]:
    """Compute profit & loss summary across all resolved bets.

    Returns:
        Dictionary with keys: ``total_bets``, ``wins``, ``losses``,
        ``win_rate``, ``total_staked``, ``total_gain``, ``roi_pct``,
        ``current_bankroll``, and ``by_type`` breakdown.
    """
    try:
        data = supabase.table(TABLE).select("*").in_("status", ["won", "lost"]).execute().data
    except Exception as e:
        logger.exception("Erreur lecture P&L")
        return {"error": str(e)}

    if not data:
        return {
            "total_bets": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_staked": 0.0,
            "total_gain": 0.0,
            "roi_pct": 0.0,
            "current_bankroll": get_current_bankroll(),
            "by_type": {},
        }

    wins = sum(1 for d in data if d["status"] == "won")
    losses = sum(1 for d in data if d["status"] == "lost")
    total = wins + losses
    total_staked = sum(float(d["stake"]) for d in data)
    total_gain = sum(float(d["actual_gain"]) for d in data)

    # Par type de ticket
    by_type: dict[str, dict[str, Any]] = {}
    for d in data:
        t = d.get("ticket_type", "unknown")
        if t not in by_type:
            by_type[t] = {"bets": 0, "wins": 0, "staked": 0.0, "gain": 0.0}
        by_type[t]["bets"] += 1
        if d["status"] == "won":
            by_type[t]["wins"] += 1
        by_type[t]["staked"] += float(d["stake"])
        by_type[t]["gain"] += float(d["actual_gain"])

    for t in by_type:
        bt = by_type[t]
        bt["win_rate"] = round(bt["wins"] / bt["bets"] * 100, 1) if bt["bets"] > 0 else 0
        bt["roi_pct"] = round(bt["gain"] / bt["staked"] * 100, 2) if bt["staked"] > 0 else 0

    return {
        "total_bets": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "total_staked": round(total_staked, 2),
        "total_gain": round(total_gain, 2),
        "roi_pct": round(total_gain / total_staked * 100, 2) if total_staked > 0 else 0,
        "current_bankroll": get_current_bankroll(),
        "by_type": by_type,
    }


def get_bankroll_history() -> list[dict[str, Any]]:
    """Retrieve the full bankroll history for plotting.

    Returns:
        List of dicts with ``date``, ``bankroll_after``, ``ticket_type``,
        and ``status`` keys, sorted chronologically.
    """
    try:
        data = (
            supabase.table(TABLE)
            .select("date, bankroll_after, ticket_type, status, actual_gain")
            .order("created_at", desc=False)
            .execute()
            .data
        )
        return data or []
    except Exception:
        logger.exception("Erreur lecture historique bankroll")
        return []
