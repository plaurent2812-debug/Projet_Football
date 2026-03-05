def test_regression(name, season_goals, season_shots, l5_goals, l5_shots):
    # Minimum sample
    if season_shots < 20 or l5_shots < 5:
        print(f"{name:15}: Insufficient sample.")
        return 1.0

    season_pct = season_goals / season_shots
    l5_pct = l5_goals / l5_shots
    diff = season_pct - l5_pct

    # Regression multiplier
    # If diff > 0, L5 is worse than season -> "Due" -> multiplier > 1
    # If diff < 0, L5 is better than season -> "Hot" -> multiplier < 1

    # Scale: max +/- 20% impact
    # Example: A true 15% shooter shooting 0% over an 18-shot streak -> diff = +0.15 -> +15% boost (1.15)

    multiplier = 1.0
    if abs(diff) > 0.05:  # Only trigger on significant deviation
        # Cap the impact at +/- 0.25 (25%)
        impact = max(-0.25, min(0.25, diff))
        # Add a confidence weight based on L5 shot volume (more shots = stronger regression sign)
        weight = min(1.0, l5_shots / 20.0)
        multiplier = 1.0 + (impact * weight)

    print(
        f"{name:15} | S_Pct: {season_pct * 100:4.1f}% | L5_Pct: {l5_pct * 100:4.1f}% | Diff: {diff * 100:5.1f}% | Multiplier: {multiplier:.3f}"
    )
    return multiplier


test_regression("Cold Sniper", 30, 200, 0, 18)  # 15% -> 0% (Due for a goal)
test_regression("Hot Plug", 4, 40, 3, 6)  # 10% -> 50% (Unsustainably hot)
test_regression("Steady Star", 40, 250, 4, 25)  # 16% -> 16% (Normal)
test_regression("Low Vol", 2, 10, 1, 3)  # (Ignored)
