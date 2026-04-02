import math

def calculate_vorp_impact(missing_players: list[dict], team_stats: dict) -> tuple[float, float]:
    """
    Calculate the Value Over Replacement Player (VORP) impact for a list of missing players.

    This function shifts from static injury thresholds to a continuous metric
    based on the missing players' performance relative to a "replacement level"
    player in the same squad.

    Args:
        missing_players: List of dictionaries, each representing a sidelined player.
                         Should contain metrics like 'rating', 'goals_per_90', 'xg_per_90',
                         'assists', 'minutes_played'.
        team_stats: Dictionary containing average team metrics for baseline comparison.

    Returns:
        Tuple of (attack_factor, defense_factor) representing the remaining strength of the team.
        Values are typically between 0.70 and 1.0 (e.g. 0.92 means 92% strength retained).
    """

    if not missing_players:
        return 1.0, 1.0

    attack_loss = 0.0
    defense_loss = 0.0

    # Replacement level baseline (e.g. a bench player rating is around 6.5)
    REPLACEMENT_RATING = 6.5

    for p in missing_players:
        # Determine the player's core rating
        rating = float(p.get("rating") or REPLACEMENT_RATING)
        # Weight by importance in squad (minutes played)
        minutes = int(p.get("minutes_played") or 0)
        
        # If the player didn't play much, their absence has low impact
        # Threshold depends on position: defenders/GKs need fewer minutes to be considered impactful
        position = p.get("position", "Unknown")
        min_minutes = 100 if position in ("Goalkeeper", "Defender") else 150
        if minutes < min_minutes and rating < 6.8:
            continue

        # Calculate raw positive vorp
        vorp = max(0.0, rating - REPLACEMENT_RATING)
        
        # Determine if player is offensive or defensive biased
        pos = p.get("position", "Unknown").lower()
        if pos in ["attacker", "forward", "winger", "midfielder", "amc"]:
            attack_loss += vorp * 0.05  # Scale factor
            if pos == "midfielder":
                defense_loss += vorp * 0.02
        elif pos in ["defender", "goalkeeper", "dmc"]:
            defense_loss += vorp * 0.06
            if pos == "defender":
                attack_loss += vorp * 0.01

    # Cap maximum disruption to a realistic limit (a single team can't drop past 60% strength)
    attack_factor = max(0.60, 1.0 - attack_loss)
    defense_factor = max(0.60, 1.0 - defense_loss)

    return round(attack_factor, 3), round(defense_factor, 3)
