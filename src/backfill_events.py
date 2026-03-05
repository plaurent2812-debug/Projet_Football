import time

from src.config import api_get, logger, supabase


def run():
    # Get last 150 FT fixtures
    data = (
        supabase.table("fixtures")
        .select("id, api_fixture_id, home_team, away_team, events_json")
        .neq("status", "NS")
        .order("date", desc=True)
        .limit(150)
        .execute()
    )
    fixtures = data.data or []
    logger.info(f"Checking {len(fixtures)} fixtures for missing player_IDs in events...")
    updated_count = 0

    for fix in fixtures:
        events = fix.get("events_json") or []
        if not events:
            continue

        # Check if any event has 'player' but no 'player_id'
        needs_update = any(ev.get("player") and "player_id" not in ev for ev in events)
        if not needs_update:
            continue

        logger.info(
            f"Updating events for {fix.get('home_team')} vs {fix.get('away_team')} (ID: {fix['api_fixture_id']})"
        )
        api_fid = fix["api_fixture_id"]

        # Fetch from API
        resp = api_get("fixtures/events", {"fixture": api_fid})
        time.sleep(0.3)
        if not resp or not resp.get("response"):
            continue

        raw_events = resp["response"]
        goals_list = []
        for ev in raw_events:
            if ev.get("type") == "Goal" and ev.get("comments") != "Penalty Shootout":
                goals_list.append(
                    {
                        "team": ev.get("team", {}).get("name", ""),
                        "player": ev.get("player", {}).get("name", ""),
                        "player_id": ev.get("player", {}).get("id"),
                        "assist": ev.get("assist", {}).get("name", "") if ev.get("assist") else "",
                        "assist_id": ev.get("assist", {}).get("id") if ev.get("assist") else None,
                        "time": ev.get("time", {}).get("elapsed", ""),
                        "extra_time": ev.get("time", {}).get("extra"),
                        "detail": ev.get("detail", ""),
                        "comments": ev.get("comments", ""),
                        "half": "1H" if (ev.get("time", {}).get("elapsed", 0) or 0) <= 45 else "2H",
                    }
                )

        supabase.table("fixtures").update({"events_json": goals_list}).eq(
            "api_fixture_id", api_fid
        ).execute()
        updated_count += 1

    logger.info(f"Done. Updated {updated_count} matches.")


if __name__ == "__main__":
    run()
