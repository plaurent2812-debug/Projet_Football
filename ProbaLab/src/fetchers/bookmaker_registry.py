"""Registre stable des bookmakers FR ciblés par SS1.

Source The Odds API v4 : https://the-odds-api.com/sports-odds-data/betting-markets.html
Les clés bookmaker sont celles exposées par l'endpoint /v4/sports/{sport}/odds.
"""
from __future__ import annotations

BOOKMAKERS_FR: list[str] = [
    "pinnacle",  # benchmark CLV interne (sharp book)
    "betclic",
    "winamax",
    "unibet",
    "zebet",
]

# Nos noms internes → clés The Odds API
# (valeurs à valider en live avec /v4/sports/{sport}/odds?bookmakers=...)
ODDS_API_KEY_BY_BOOKMAKER: dict[str, str] = {
    "pinnacle": "pinnacle",
    "betclic": "betclic",
    "winamax": "winamax_fr",
    "unibet": "unibet_fr",
    "zebet": "zebet",
}

# Sport keys The Odds API (v4)
SPORT_KEYS: dict[str, list[str]] = {
    "football": [
        "soccer_france_ligue_one",     # Ligue 1
        "soccer_france_ligue_two",     # Ligue 2
        "soccer_epl",                  # Premier League
        "soccer_spain_la_liga",        # La Liga
        "soccer_italy_serie_a",        # Serie A
        "soccer_germany_bundesliga",   # Bundesliga
        "soccer_uefa_champs_league",   # UCL
        "soccer_uefa_europa_league",   # UEL
    ],
    "nhl": ["icehockey_nhl"],
}


def get_bookmaker_from_api_key(api_key: str) -> str | None:
    """Inverse lookup : The Odds API key → nom interne."""
    for internal, api in ODDS_API_KEY_BY_BOOKMAKER.items():
        if api == api_key:
            return internal
    return None


def normalize_bookmaker(name: str) -> str:
    """Normalise un nom arbitraire → nom interne canonique.

    Accepte les aliases (casse, espaces). Lève ValueError si inconnu.
    """
    candidate = name.strip().lower()
    if candidate in BOOKMAKERS_FR:
        return candidate
    raise ValueError(f"Unknown bookmaker: {name!r} — expected one of {BOOKMAKERS_FR}")


def normalize_team_name(name: str) -> str:
    """Normalise un nom d'équipe arbitraire pour matching cross-provider.

    Applique (dans l'ordre) :
      - strip + lowercase
      - suppression des ponctuations ('.', ',', '-')
      - normalisation des espaces multiples
      - drop des suffixes NHL instables ("hockey club", "mammoth")
      - rename map explicite pour les cas documentés (Utah rebrand 2025-26)

    Reference : leçon 69 de tasks/lessons.md (NHL + foot cross-provider drift).
    """
    if not isinstance(name, str):
        return ""
    s = name.strip().lower()
    # Ponctuations courantes
    for ch in (".", ","):
        s = s.replace(ch, "")
    # Normaliser les espaces
    s = " ".join(s.split())
    # Suffixes NHL fragiles
    for suffix in (" hockey club", " mammoth"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    # Renames explicites (Utah 2025-26)
    rename_map = {
        "utah": "utah",  # placeholder — Utah est déjà canonique après drop suffix
        "paris saint germain": "paris saint-germain",
    }
    s = rename_map.get(s, s)
    return s


def teams_match(a: str, b: str) -> bool:
    """Compare deux noms d'équipe après normalisation (lesson 69)."""
    return normalize_team_name(a) == normalize_team_name(b)
