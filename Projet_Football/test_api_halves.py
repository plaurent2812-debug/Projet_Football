import sys
import os

# Add parent directory to path to import fetchers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.api import api_get
import json

fix_id = 1148418 # or any finished match

print("Fetching stats for", fix_id)
# 1. Try passing half=1 or similar? Actually API-Sports documentation doesnt mention `half` for `fixtures/statistics`.
resp = api_get("fixtures/statistics", {"fixture": fix_id})
print("Result type:", type(resp))
if resp and "response" in resp:
    print(json.dumps(resp["response"], indent=2)[:1000])

