import sys, os
import requests
sys.path.insert(0, os.path.abspath("Projet_Football"))
from config import API_FOOTBALL_KEY

api_id = 2025020910
HOCKEY_API_URL = "https://v1.hockey.api-sports.io"
HOCKEY_HEADERS = {
    "x-rapidapi-host": "v1.hockey.api-sports.io",
    "x-rapidapi-key": API_FOOTBALL_KEY,
}
resp = requests.get(
    f"{HOCKEY_API_URL}/games",
    headers=HOCKEY_HEADERS,
    params={"id": api_id},
)
print(resp.status_code)
print(resp.json())
