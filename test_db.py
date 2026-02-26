import sys, os
sys.path.insert(0, os.path.abspath("Projet_Football"))
from config import supabase

data = supabase.table("nhl_fixtures").select("home_team, status, home_score").gte("date", "2026-02-26").execute().data
for row in data:
    print(row)
