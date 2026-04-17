"""
Récupération des cotes NHL (h2h + totals) via The Odds API.

Provider choisi : https://api.the-odds-api.com (plan Free = 500 req/mois)
— API-Sports Hockey Free ne retourne aucune cote pour NHL, d'où ce switch.

Le format de sortie écrit dans nhl_fixtures.odds_json reproduit celui
d'API-Sports (bookmakers > bets > values) pour rester compatible avec
dashboard/src/pages/NHL/NHLMatchDetail.tsx:192-204 qui calcule les EV.

Coût mensuel typique : 2 runs/jour × 1 req bulk = ~60/500 req/mois.
"""

import os
import re
from datetime import datetime, timedelta, timezone

import requests

from src.config import logger, supabase

# The Odds API — bulk endpoint renvoie tous les events NHL avec
# markets=h2h,totals en 1 seule requête (vs 1 req par event).
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "icehockey_nhl"
REGIONS = "us"
MARKETS = "h2h,totals"

# Fenêtre temporelle : matchs NS dans les 36h qui viennent.
# 36h au lieu de "today UTC" pour couvrir les matchs de soirée US qui
# commencent après minuit UTC (COL @ 00:00, SJS @ 02:00 UTC lors des
# grosses soirées samedi).
UPCOMING_WINDOW_HOURS = 36

# EV threshold affiché en log (le frontend re-calcule de toute façon).
_EV_LOG_THRESHOLD = 0.02


def _normalize_team(name: str) -> str:
    """Normalise un nom d'équipe pour matching tolérant entre providers.

    Gère les divergences connues :
      - 'St. Louis Blues' (NHL API) vs 'St Louis Blues' (Odds API) : point
      - 'Utah Hockey Club' (NHL API) vs 'Utah Mammoth' (Odds API) : rename 2025-26
    """
    s = (name or "").lower().replace(".", "").replace("'", "")
    s = re.sub(r"\s+", " ", s).strip()
    # Utah a changé de nom pour la saison 2025-26 — la DB et l'API divergent
    s = s.replace("hockey club", "").replace("mammoth", "").strip()
    return s


def _fetch_bulk_odds(api_key: str) -> list[dict]:
    """Récupère tous les events NHL avec cotes h2h+totals en 1 requête."""
    resp = requests.get(
        f"{ODDS_API_BASE}/sports/{SPORT}/odds",
        params={
            "apiKey": api_key,
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": "decimal",
        },
        timeout=20,
    )
    remaining = resp.headers.get("x-requests-remaining", "?")
    if resp.status_code != 200:
        logger.error(
            "[NHL Odds] The Odds API HTTP %d (remaining=%s): %s",
            resp.status_code,
            remaining,
            resp.text[:200],
        )
        return []
    logger.info(
        "[NHL Odds] The Odds API quota remaining: %s (used=%s)",
        remaining,
        resp.headers.get("x-requests-used", "?"),
    )
    return resp.json() or []


def _build_odds_json(event: dict, home_team: str, away_team: str, fetched_at: str) -> dict:
    """Transforme la réponse The Odds API vers le format odds_json attendu
    par le frontend (bookmakers > bets > values).

    Structure cible (cf. NHLMatchDetail.tsx:194-204) :
        {
          "bookmakers": [
            {
              "key": "draftkings",
              "title": "DraftKings",
              "bets": [
                {"id": 1, "name": "Home/Away",
                 "values": [{"value": "Home", "odd": "2.10"},
                            {"value": "Away", "odd": "1.75"}]},
                {"id": 10, "name": "Over/Under 6.0",
                 "values": [{"value": "Over", "odd": "1.93"},
                            {"value": "Under", "odd": "1.85"}]}
              ]
            }
          ],
          "source": "the-odds-api",
          "fetched_at": "2026-04-10T23:05:28+00:00"
        }
    """
    home_norm = _normalize_team(home_team)
    away_norm = _normalize_team(away_team)
    bookmakers: list[dict] = []

    for bm in event.get("bookmakers", []):
        bets: list[dict] = []
        for mkt in bm.get("markets", []):
            if mkt.get("key") == "h2h":
                values = []
                for o in mkt.get("outcomes", []):
                    o_norm = _normalize_team(o.get("name", ""))
                    price = o.get("price")
                    if price is None:
                        continue
                    if o_norm == home_norm:
                        values.append({"value": "Home", "odd": f"{float(price):.2f}"})
                    elif o_norm == away_norm:
                        values.append({"value": "Away", "odd": f"{float(price):.2f}"})
                if len(values) == 2:
                    bets.append({"id": 1, "name": "Home/Away", "values": values})

            elif mkt.get("key") == "totals":
                # Un bookmaker peut exposer plusieurs lignes (ex: 5.5 et 6.0).
                # On génère un "bet" par ligne pour que le frontend puisse
                # piocher la ligne qu'il veut.
                lines: dict[float, list[dict]] = {}
                for o in mkt.get("outcomes", []):
                    point = o.get("point")
                    price = o.get("price")
                    if point is None or price is None:
                        continue
                    lines.setdefault(float(point), []).append(
                        {"value": o.get("name", ""), "odd": f"{float(price):.2f}"}
                    )
                for pt in sorted(lines):
                    bets.append({"id": 10, "name": f"Over/Under {pt}", "values": lines[pt]})

        if bets:
            bookmakers.append(
                {
                    "key": bm.get("key"),
                    "title": bm.get("title"),
                    "bets": bets,
                }
            )

    return {
        "bookmakers": bookmakers,
        "source": "the-odds-api",
        "fetched_at": fetched_at,
    }


def fetch_nhl_odds() -> dict:
    """Fetch bulk NHL odds et update nhl_fixtures.odds_json pour les matchs NS
    à venir dans les 36h.

    Returns:
        {"status": "ok", "updated": int, "skipped": int, "errors": int}
    """
    logger.info("[NHL Odds] Démarrage (provider=the-odds-api)")

    api_key = os.getenv("ODDS_API_KEY", "")
    if not api_key:
        logger.error("[NHL Odds] ODDS_API_KEY manquante — abort")
        return {"status": "error", "reason": "ODDS_API_KEY missing"}

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=UPCOMING_WINDOW_HOURS)

    # 1. Fixtures à enrichir (fenêtre glissante, status NS uniquement)
    fixtures = (
        supabase.table("nhl_fixtures")
        .select("id, home_team, away_team, date")
        .gte("date", now.isoformat())
        .lt("date", window_end.isoformat())
        .in_("status", ["NS"])
        .execute()
        .data
        or []
    )

    if not fixtures:
        logger.info(
            "[NHL Odds] Aucun match NS dans les %dh à venir.",
            UPCOMING_WINDOW_HOURS,
        )
        return {"status": "ok", "updated": 0, "skipped": 0, "errors": 0}

    logger.info(
        "[NHL Odds] %d matchs NS trouvés (fenêtre %dh)",
        len(fixtures),
        UPCOMING_WINDOW_HOURS,
    )

    # 2. Bulk fetch (1 requête pour tous les events)
    events = _fetch_bulk_odds(api_key)
    if not events:
        logger.warning("[NHL Odds] Aucun event retourné par The Odds API")
        return {"status": "ok", "updated": 0, "skipped": len(fixtures), "errors": 0}

    # 3. Index events par (home_norm, away_norm) pour matching tolérant
    event_index: dict[tuple[str, str], dict] = {
        (_normalize_team(ev.get("home_team", "")), _normalize_team(ev.get("away_team", ""))): ev
        for ev in events
    }

    fetched_at = now.isoformat()
    updated = 0
    skipped = 0
    errors = 0

    for fix in fixtures:
        key = (_normalize_team(fix["home_team"]), _normalize_team(fix["away_team"]))
        ev = event_index.get(key)
        if not ev:
            logger.warning(
                "[NHL Odds] Pas d'event matché pour %s vs %s",
                fix["home_team"],
                fix["away_team"],
            )
            skipped += 1
            continue

        try:
            odds_json = _build_odds_json(ev, fix["home_team"], fix["away_team"], fetched_at)
            if not odds_json["bookmakers"]:
                logger.warning(
                    "[NHL Odds] Event matché mais 0 bookmaker exploitable pour %s vs %s",
                    fix["home_team"],
                    fix["away_team"],
                )
                skipped += 1
                continue

            supabase.table("nhl_fixtures").update({"odds_json": odds_json}).eq(
                "id", fix["id"]
            ).execute()
            updated += 1
            logger.info(
                "[NHL Odds] ✅ %s vs %s (%d bookmakers)",
                fix["home_team"],
                fix["away_team"],
                len(odds_json["bookmakers"]),
            )
        except Exception as e:
            logger.error(
                "[NHL Odds] Échec update %s vs %s: %s",
                fix["home_team"],
                fix["away_team"],
                e,
            )
            errors += 1

    logger.info(
        "[NHL Odds] Fin: %d mis à jour, %d skipped, %d erreurs",
        updated,
        skipped,
        errors,
    )
    return {"status": "ok", "updated": updated, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    fetch_nhl_odds()
