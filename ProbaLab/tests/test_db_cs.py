import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src.config import supabase

# V\u00e9rifie l'ensemble des donn\u00e9es disponibles
res = (
    supabase.table("player_season_stats").select("*").eq("player_api_id", 162453).limit(5).execute()
)
print(res.data)
