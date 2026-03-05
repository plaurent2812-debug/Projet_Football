import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src.config import supabase

res = supabase.table("player_season_stats").select("*").limit(1).execute()
print(res.data[0].keys())
