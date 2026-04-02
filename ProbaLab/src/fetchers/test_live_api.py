import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import api_get


def test_live_fixtures():
    data = api_get("fixtures", {"live": "all"})
    if not data or not data.get("response"):
        print("No live fixtures right now.")
        return

    first_match = data["response"][0]
    print(list(first_match.keys()))
    if "statistics" in first_match:
        print("Statistics ARE included in /fixtures?live=all")
    else:
        print("Statistics ARE NOT included in /fixtures?live=all")


if __name__ == "__main__":
    test_live_fixtures()
