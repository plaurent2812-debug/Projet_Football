import requests
import json
import os

from dotenv import load_dotenv
load_dotenv(".env")

url = "https://v3.football.api-sports.io/fixtures/statistics?fixture=1148418" # take some fixture id
headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': os.getenv("API_KEY", "") 
}
# Try with half=1 or type=half
print("Testing /fixtures/statistics...")
response = requests.request("GET", url, headers=headers)
print("Standard:", json.dumps(response.json(), indent=2)[:500])

url2 = url + "&half=1"
response2 = requests.request("GET", url2, headers=headers)
print("Half=1:", json.dumps(response2.json(), indent=2)[:500])

