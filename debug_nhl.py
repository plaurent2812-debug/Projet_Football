from src.config import supabase

resp = supabase.table("nhl_suivi_algo_clean").select("*").limit(10).execute()
for r in resp.data:
    print(r)
