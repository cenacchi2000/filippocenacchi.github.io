import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

def read(url, headers=None):
    with urlopen(Request(url, headers=headers or {}), timeout=25) as response:
        return response.read()

def citations():
    page = BeautifulSoup(read("https://scholar.google.com/citations?user=jkBG6hcAAAAJ&hl=en"), "html.parser")
    for row in page.select("#gsc_rsb_st tr"):
        cells = row.find_all("td")
        if len(cells) >= 2 and cells[0].get_text(strip=True) == "Citations":
            value = cells[1].get_text(strip=True)
            if re.fullmatch(r"[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+", value):
                return int(value.replace(",", ""))
    raise ValueError("Citation total unavailable")

def followers():
    token = os.environ.get("LINKEDIN_TOKEN")
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN is missing")
    data = read("https://api.linkedin.com/rest/memberFollowersCount?q=me", {
        "Authorization": "Bearer " + token,
        "LinkedIn-Version": "202606",
        "X-Restli-Protocol-Version": "2.0.0",
    })
    return json.loads(data)["elements"][0]["memberFollowersCount"]

path = Path("profile-metrics.json")
metrics = json.loads(path.read_text()) if path.exists() else {}
for label, fetch in (("citations", citations), ("followers", followers)):
    try:
        count = fetch()
        if type(count) is not int or count < 0:
            raise ValueError("Invalid count")
        if metrics.get(label, {}).get("count") != count:
            metrics[label] = {"count": count, "date": datetime.now(ZoneInfo("Australia/Sydney")).strftime("%d %B %Y")}
    except Exception as exc:
        print(f"::warning::{label}: {exc}")
path.write_text(json.dumps(metrics, indent=2) + "\n")
