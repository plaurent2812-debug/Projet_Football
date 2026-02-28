import sys, os
from supabase import create_client
sys.path.insert(0, os.path.abspath("Projet_Football"))
from Projet_Football.config import supabase

# Verifie les stats pour O. Dembele (api_id=153)
res = supabase.table("player_season_stats").select("*").eq("player_api_id", 153).execute()
for r in res.data:
    print(r)
