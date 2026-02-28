import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# We need the DATABASE_URL to connect with psycopg2
# Often Supabase provides this in the format postgresql://user:password@host:port/dbname
# The project has SUPABASE_URL and SUPABASE_KEY, but they are for the REST API.
# Does the .env have a DB URL? Let's check.
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found in .env. We cannot run SQL commands directly via Python.")
    print("Please run the content of migrations/009_football_players.sql in the Supabase SQL editor.")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    with open("migrations/009_football_players.sql", "r") as f:
        sql = f.read()
        
    cur.execute(sql)
    conn.commit()
    print("Table football_players created successfully.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error executing migration: {e}")
    exit(1)
