import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import os
import sys
import yaml
from collections import Counter
from dotenv import load_dotenv

# load .env from project root
load_dotenv()

from extractors.core.api_client import APIFootballClient

cfg_path = sys.argv[1]
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

api_key = os.getenv("APIFOOTBALL_KEY")
if not api_key:
    raise RuntimeError("APIFOOTBALL_KEY missing. Put it in .env")

client = APIFootballClient(api_key=api_key, request_delay=0)

comp_id = cfg["competition_id"]
season = cfg["season"]

fx = client.fetch_season_fixtures(comp_id, season)
rounds = [((x.get("league") or {}).get("round", "")) for x in fx]
c = Counter([r for r in rounds if r])

for k, v in c.most_common():
    print(f"{k} | {v}")

print("\nTOTAL fixtures:", len(fx))
