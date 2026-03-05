import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath("Projet_Football"))
from src.config import supabase

today = datetime.now().strftime("%Y-%m-%d")
print("Today is", today)
fixtures = (
    supabase.table("nhl_fixtures")
    .select("id, api_fixture_id, home_team, away_team, status, date")
    .gte("date", f"{today}T00:00:00Z")
    .lt("date", f"{today}T23:59:59Z")
    .execute()
    .data
    or []
)
print("Found fixtures:", len(fixtures))
for f in fixtures[:3]:
    print(f)
