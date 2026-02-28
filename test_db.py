import sys, os
from supabase import create_client

sys.path.insert(0, os.path.abspath("Projet_Football"))
from Projet_Football.config import supabase

res = supabase.table("player_season_stats").select("*").limit(1).execute()
print(res.data[0].keys())
