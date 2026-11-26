"""Refresh exact public profile counts; failures never overwrite verified values."""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

SCHOLAR_URL = "https://scholar.google.com/citations?user=jkBG6hcAAAAJ&hl=en"
LINKEDIN_URL = "https://www.linkedin.com/in/filippo-cenacchi/"


def read(url, headers=None):
    headers = {"User-Agent": "ProfileMetrics/1.0 (+https://github.com/cenacchi2000/filippocenacchi.github.io)",
               "Accept-Language": "en", **(headers or {})}
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        return response.read()


def exact_count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+", value.strip()):
        return int(value.strip().replace(",", ""))
    raise ValueError("An exact nonnegative count was not available")


def parse_citations(html):
    page = BeautifulSoup(html, "html.parser")
    name = page.select_one("#gsc_prf_in")
    if not name or name.get_text(" ", strip=True).casefold() != "filippo cenacchi":
        raise ValueError("Scholar profile identity could not be verified")
    for row in page.select("#gsc_rsb_st tr"):
        cells = row.find_all("td")
        if len(cells) >= 2 and cells[0].get_text(strip=True) == "Citations":
            return exact_count(cells[1].get_text(strip=True))
    raise ValueError("Scholar citation total unavailable")


def citations():
    return parse_citations(read(SCHOLAR_URL)), "google-scholar"


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def own_profile(value):
    if not isinstance(value, str):
        return False
    url = urlsplit(value)
    return url.hostname in {"linkedin.com", "www.linkedin.com", "au.linkedin.com"} and url.path.rstrip("/") == "/in/filippo-cenacchi"


def parse_followers(html):
    page = BeautifulSoup(html, "html.parser")
    counts = set()
    for script in page.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        for person in objects(data):
            types = person.get("@type", [])
            if isinstance(types, str):
                types = [types]
            if "Person" not in types or not own_profile(person.get("url", person.get("@id"))):
                continue
            stats = person.get("interactionStatistic", [])
            if isinstance(stats, dict):
                stats = [stats]
            for stat in stats:
                action = stat.get("interactionType", {})
                action = action.get("@type", "") if isinstance(action, dict) else action
                if action in {"FollowAction", "https://schema.org/FollowAction", "http://schema.org/FollowAction"}:
                    counts.add(exact_count(stat.get("userInteractionCount")))
    if len(counts) == 1:
        return counts.pop()
    if len(counts) > 1:
        raise ValueError("Conflicting LinkedIn follower totals")
    # Restrict visible text to the owner's top card, excluding suggested profiles/posts.
    card = page.select_one(".top-card-layout")
    if card:
        name = card.select_one("h1")
        if name and name.get_text(" ", strip=True).casefold() == "filippo cenacchi":
            matches = re.findall(r"(?<![\w.,])([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+) followers\b", card.get_text(" ", strip=True))
            counts = {exact_count(match) for match in matches}
            if len(counts) == 1:
                return counts.pop()
    raise ValueError("Exact public LinkedIn follower count unavailable; keeping last verified count")


def followers():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN") or os.environ.get("LINKEDIN_TOKEN")
    if token:
        try:
            data = json.loads(read("https://api.linkedin.com/rest/memberFollowersCount?q=me", {
                "Authorization": "Bearer " + token,
                "LinkedIn-Version": datetime.now(ZoneInfo("UTC")).strftime("%Y%m"),
                "X-Restli-Protocol-Version": "2.0.0",
            }))
            return exact_count(data["elements"][0]["memberFollowersCount"]), "linkedin-api"
        except Exception:
            print("::warning::LinkedIn API unavailable; trying the public profile")
    return parse_followers(read(LINKEDIN_URL)), "linkedin-public-profile"


def refresh(path=Path("profile-metrics.json")):
    metrics = json.loads(path.read_text())
    today = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%d %B %Y")
    successes = 0
    lines = ["## Profile metrics", "", "| Metric | Result |", "| --- | --- |"]
    for label, fetch in (("citations", citations), ("followers", followers)):
        try:
            count, source = fetch()
            count = exact_count(count)
            metrics[label] = {"count": count, "date": today, "source": source}
            successes += 1
            lines.append(f"| {label} | Verified: {count:,} ({source}) |")
        except Exception as exc:
            # Do not log response bodies or tokens.
            detail = f"HTTP {exc.code}" if isinstance(exc, HTTPError) else type(exc).__name__
            print(f"::warning::{label}: update unavailable ({detail}); retained verified value")
            lines.append(f"| {label} | Unavailable; retained last verified count and date |")
    content = json.dumps(metrics, indent=2) + "\n"
    if successes and content != path.read_text():
        path.write_text(content)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as file:
            file.write("\n".join(lines) + "\n")
    return successes


if __name__ == "__main__":
    if not refresh():
        print("::warning::No fresh metrics verified; existing counts and dates retained.")
