"""
nhl/constants.py — Centralized NHL team mappings.

Single source of truth for all NHL abbreviation ↔ name conversions.
"""

from __future__ import annotations

# Abbreviation → Full name
NHL_TEAM_NAMES: dict[str, str] = {
    "ANA": "Anaheim Ducks",
    "BOS": "Boston Bruins",
    "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames",
    "CAR": "Carolina Hurricanes",
    "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche",
    "CBJ": "Columbus Blue Jackets",
    "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings",
    "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings",
    "MIN": "Minnesota Wild",
    "MTL": "Montréal Canadiens",
    "NSH": "Nashville Predators",
    "NJD": "New Jersey Devils",
    "NYI": "New York Islanders",
    "NYR": "New York Rangers",
    "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins",
    "SJS": "San Jose Sharks",
    "SEA": "Seattle Kraken",
    "STL": "St. Louis Blues",
    "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club",
    "VAN": "Vancouver Canucks",
    "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals",
    "WPG": "Winnipeg Jets",
}

# Full name → Abbreviation (reverse mapping)
NHL_NAME_TO_ABBREV: dict[str, str] = {v: k for k, v in NHL_TEAM_NAMES.items()}
# Also add common alternate spellings
NHL_NAME_TO_ABBREV["Montreal Canadiens"] = "MTL"


def get_nhl_season_id() -> str:
    """Calculate the current NHL season ID (e.g. '20252026').

    NHL seasons start in October. The season ID uses the calendar year
    the season started in followed by the next year.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    start_year = now.year if now.month >= 8 else now.year - 1
    return f"{start_year}{start_year + 1}"


# Common statuses for finished NHL matches across different APIs/sources
NHL_FINISHED_STATUSES: set[str] = {"FT", "Final", "FINAL", "OFF", "Official"}
