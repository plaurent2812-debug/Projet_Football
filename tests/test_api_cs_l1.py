import json
import os
import sys

import requests

sys.path.insert(0, os.path.abspath("."))
from src.config import API_FOOTBALL_KEY

resp = requests.get(
    "https://v3.football.api-sports.io/players",
    headers={"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": API_FOOTBALL_KEY},
    params={"team": 85, "season": 2024},
).json()

if resp and resp.get("response"):
    print(json.dumps(resp["response"][0]["statistics"][0], indent=2))
