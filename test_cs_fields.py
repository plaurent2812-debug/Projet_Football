import sys, os
import requests
import json
sys.path.insert(0, os.path.abspath("Projet_Football"))
from Projet_Football.config import API_FOOTBALL_KEY

resp = requests.get(
    "https://v3.football.api-sports.io/players",
    headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": API_FOOTBALL_KEY},
    params={"team": 85, "season": 2024},
).json()

if resp and resp.get("response"):
    for item in resp["response"]:
        player = item["player"]
        if player["name"] == "G. Donnarumma":
            print(json.dumps(item["statistics"], indent=2))
