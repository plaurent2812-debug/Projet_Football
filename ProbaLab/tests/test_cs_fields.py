import json
import os

import pytest
import requests

from src.config import API_FOOTBALL_KEY

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_API_TESTS") != "1",
        reason="Live API-Football probe; set RUN_LIVE_API_TESTS=1 to run.",
    ),
]


def test_player_clean_sheet_statistics_shape_probe():
    resp = requests.get(
        "https://v3.football.api-sports.io/players",
        headers={
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": API_FOOTBALL_KEY,
        },
        params={"team": 85, "season": 2024},
        timeout=20,
    ).json()

    assert resp.get("response"), resp
    donnarumma = [
        item for item in resp["response"] if item.get("player", {}).get("name") == "G. Donnarumma"
    ]
    assert donnarumma
    assert json.dumps(donnarumma[0]["statistics"])
