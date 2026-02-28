import sys, os
import requests
sys.path.insert(0, os.path.abspath("Projet_Football"))
from Projet_Football.config import API_FOOTBALL_KEY

HOCKEY_API_URL = "https://v3.football.api-sports.io"
HOCKEY_HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-rapidapi-key": API_FOOTBALL_KEY,
}
resp = requests.get(
    f"{HOCKEY_API_URL}/players",
    headers=HOCKEY_HEADERS,
    params={"team": 85, "season": 2024},
).json()

if resp and resp.get("response"):
    for item in resp["response"]:
        player = item["player"]
        if player["name"] == "G. Donnarumma":
            print(item["statistics"][0])
