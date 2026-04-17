from src.config import supabase

user_id = "754e5844-cca5-45e0-8c6c-4fbed48f2642"
print("Test 1 (eq id, user_id):")
res1 = supabase.table("profiles").select("role").eq("id", user_id).execute()
print(res1.data)

print("\nTest 2 (eq id, str(user_id) single):")
res2 = supabase.table("profiles").select("role").eq("id", str(user_id)).single().execute()
print(res2.data)
